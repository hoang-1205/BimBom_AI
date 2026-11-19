"""Train BimBom with successful-step accounting, finite-state guards and early stopping."""
import argparse
import hashlib
import json
import math
import os
import platform
import signal
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
import torch
import tokenizers
import torch.nn.functional as F
import Chinh_Che_Do as C
from Model_BimBomAI.pipeline import ROOT, LanguageModel, prepare, generate
from Model_BimBomAI.Ma_Nguon.checkpoint import validate, find_best, optimizer_steps
from Model_BimBomAI.Ma_Nguon.data import prepare_sft, training_batch, label_positions
from Model_BimBomAI.Ma_Nguon.runtime import session_lock, atomic_json, append_json, stop_requested, read_input
from Model_BimBomAI.Ma_Nguon.archive import snapshot_sources, archive_completed_inputs

_interrupt_requested = False


def safety_config(policy=None):
    values = dict(eval_every=C.EVAL_EVERY_STEPS, patience=C.EARLY_STOPPING_PATIENCE,
                  min_delta=C.EARLY_STOPPING_MIN_DELTA, early_stopping=C.EARLY_STOPPING_ENABLED,
                  max_nonfinite=C.MAX_CONSECUTIVE_NONFINITE,
                  warn_steps=C.TRAIN_WARN_ADDITIONAL_STEPS, max_steps=C.TRAIN_MAX_ADDITIONAL_STEPS)
    if policy is not None:
        if policy not in ('stop', 'warn'):
            raise ValueError('Chế độ Early Stopping phải là stop hoặc warn.')
        values['early_stopping'] = policy == 'stop'
    if type(values['early_stopping']) is not bool:
        raise ValueError('EARLY_STOPPING_ENABLED phải là True hoặc False.')
    for key in ('eval_every', 'patience', 'max_nonfinite', 'warn_steps', 'max_steps'):
        if type(values[key]) is not int or values[key] < 1:
            raise ValueError(f'Cấu hình {key} phải là số nguyên dương.')
    if not math.isfinite(values['min_delta']) or values['min_delta'] < 0 or values['warn_steps'] > values['max_steps']:
        raise ValueError('Ngưỡng cải thiện/giới hạn bước không hợp lệ.')
    return values


def check_step_budget(extra, confirmed=False, input_fn=read_input):
    limits = safety_config()
    if type(extra) is not int or extra < 1:
        raise ValueError(f'Số bước học thêm phải là số nguyên từ 1 đến {limits["max_steps"]:,}.')
    if extra > limits['max_steps']:
        raise ValueError(f'Yêu cầu {extra:,} bước vượt TRAIN_MAX_ADDITIONAL_STEPS={limits["max_steps"]:,}. Không bắt đầu train.')
    if extra >= limits['warn_steps'] and not confirmed:
        print(f'CẢNH BÁO: sắp chạy thêm {extra:,} optimizer steps; cần xác nhận số bước lớn.', flush=True)
        if input_fn('Nhập HOC_TIEP để xác nhận số bước lớn: ').strip() != 'HOC_TIEP':
            raise ValueError('Đã hủy lần huấn luyện lớn.')


class EarlyStopping:
    def __init__(self, patience, min_delta, state=None, best=float('inf')):
        state = state or {}
        self.patience, self.min_delta = patience, min_delta
        self.best = min(best, state.get('best', float('inf')))
        self.anchor = state.get('anchor', self.best)
        if best < state.get('best', float('inf')):
            self.anchor = min(self.anchor, best)
        self.bad_evals = state.get('bad_evals', 0)
        self.last_step = state.get('last_step', -1)

    def observe(self, loss, step):
        if not math.isfinite(loss):
            raise ValueError('Validation loss NaN/Inf; không lưu checkpoint mới.')
        improved = loss < self.best
        self.best = min(self.best, loss)
        if step != self.last_step:
            if loss < self.anchor - self.min_delta:
                self.anchor, self.bad_evals = loss, 0
            else:
                self.bad_evals += 1
            self.last_step = step
        return improved

    @property
    def stopped(self):
        return self.bad_evals >= self.patience

    def state_dict(self):
        return dict(best=self.best, anchor=self.anchor, bad_evals=self.bad_evals, last_step=self.last_step)


def finite_state(model, optimizer):
    for tensor in model.state_dict().values():
        if not bool(torch.isfinite(tensor).all()):
            return False
    for state in optimizer.state.values():
        for value in state.values():
            if isinstance(value, torch.Tensor) and not bool(torch.isfinite(value).all()):
                return False
    return True


def optimizer_attempt(model, optimizer, scaler, batch_fn, accum, device, amp):
    """Return success only when Adam actually updated finite weights and state."""
    optimizer.zero_grad(set_to_none=True)
    for _ in range(accum):
        x, y = batch_fn()
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=amp):
            loss = F.cross_entropy(model(x).flatten(0, 1), y.flatten()) / accum
        scaled_loss = scaler.scale(loss)  # initialize scaler even on the first bad loss
        if not bool(torch.isfinite(loss)):
            if scaler.is_enabled():
                state = scaler.state_dict()
                scale = max(float(state['scale'] * state['backoff_factor']), torch.finfo(torch.float32).tiny)
                scaler.update(new_scale=scale)
                state.update(scale=scale, _growth_tracker=0)
                scaler.load_state_dict(state)
            optimizer.zero_grad(set_to_none=True)
            return dict(success=False, reason='nonfinite_loss', grad_norm=None, overflow=False)
        scaled_loss.backward()
    scaler.unscale_(optimizer)
    gradients = [p.grad for p in model.parameters() if p.grad is not None]
    if not gradients:
        raise RuntimeError('Không có gradient để cập nhật.')
    if any(not bool(torch.isfinite(grad).all()) for grad in gradients):
        if scaler.is_enabled():
            # unscale_ recorded found_inf: step is skipped by GradScaler, update backs off.
            scaler.step(optimizer)
            scaler.update()
        optimizer.zero_grad(set_to_none=True)
        return dict(success=False, reason='nonfinite_gradient', grad_norm=None, overflow=scaler.is_enabled())
    # Float64 norm avoids a float32 reduction overflow when individual gradients are finite.
    norm = torch.linalg.vector_norm(torch.stack([torch.linalg.vector_norm(g.detach(), dtype=torch.float64) for g in gradients]))
    if not bool(torch.isfinite(norm)):
        raise FloatingPointError('Gradient norm không hữu hạn dù gradient đã kiểm tra; dừng để bảo vệ optimizer.')
    coefficient = (1.0 / (norm + 1e-6)).clamp(max=1.0)
    for grad in gradients:
        grad.mul_(coefficient.to(device=grad.device, dtype=grad.dtype))
    before = scaler.get_scale()
    scaler.step(optimizer)
    scaler.update()
    if scaler.is_enabled() and scaler.get_scale() < before:
        return dict(success=False, reason='amp_overflow', grad_norm=float(norm), overflow=True)
    if not finite_state(model, optimizer):
        raise FloatingPointError('Trọng số/optimizer NaN/Inf sau cập nhật. Không lưu trạng thái này; dùng checkpoint hợp lệ trước đó.')
    return dict(success=True, reason=None, grad_norm=float(norm), overflow=False)


@torch.no_grad()
def evaluate_model(model, data, targets, batch_size, device, indexes=None):
    model.eval()
    scores = {}
    try:
        for name in ('train', 'validation'):
            index = indexes[name] if indexes is not None else label_positions(data[name], targets[name])
            generator = torch.Generator().manual_seed(123)
            losses = []
            for _ in range(5):
                x, y = training_batch(data[name], targets[name], model.context, batch_size, device, generator, index)
                losses.append(F.cross_entropy(model(x).flatten(0, 1), y.flatten()).item())
            scores[name + '_loss'] = sum(losses) / len(losses)
        if not all(math.isfinite(v) for v in scores.values()):
            raise FloatingPointError('Evaluation loss NaN/Inf; không lưu checkpoint mới.')
        scores['perplexity'] = math.exp(min(scores['validation_loss'], 80))
        return scores
    finally:
        model.train()


def should_stop():
    return _interrupt_requested or stop_requested()


def train_main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder', type=Path)
    p.add_argument('--steps', type=int, default=600, help='Tổng số optimizer steps THÀNH CÔNG cần đạt')
    group = p.add_mutually_exclusive_group()
    group.add_argument('--resume', type=Path)
    group.add_argument('--init-from', type=Path)
    p.add_argument('--stage', choices=['pretrain', 'sft'])
    p.add_argument('--output-root', type=Path, default=ROOT / 'Ket_Qua')
    p.add_argument('--device', choices=['cpu', 'cuda', 'auto'])
    p.add_argument('--smoke', action='store_true')
    p.add_argument('--include-approved', action='store_true')
    p.add_argument('--confirm-large-run', action='store_true', help='Xác nhận ngưỡng cảnh báo; không vượt giới hạn cứng')
    p.add_argument('--early-stopping', choices=['warn', 'stop'], help='warn: cảnh báo và học đủ bước; stop: dừng khi validation không cải thiện')
    a = p.parse_args(argv)
    limits = safety_config(a.early_stopping)
    if a.include_approved:
        p.error('Dùng --stage sft --init-from CHECKPOINT; không trộn hội thoại vào Pretrain.')
    if a.smoke and (a.resume or a.init_from):
        p.error('--smoke chỉ dùng tạo mô hình thử mới.')
    source = a.resume or a.init_from
    origin = validate(source, resume=bool(a.resume)) if source else None
    step0 = optimizer_steps(origin) if a.resume else 0
    check_step_budget(a.steps - step0, a.confirm_large_run)
    print('Chế độ validation: ' + ('dừng sớm khi không cải thiện (stop).' if limits['early_stopping']
          else 'chỉ cảnh báo (warn); không dừng vì Early Stopping, vẫn giữ checkpoint tốt nhất.'), flush=True)
    if a.resume and origin['step'] != step0:
        print(f'CẢNH BÁO checkpoint cũ ghi step={origin["step"]}, optimizer thực tế={step0}. Dùng số bước thực tế.', flush=True)
    if a.resume and a.folder:
        print('--folder được bỏ qua khi resume: dữ liệu lấy từ checkpoint.', flush=True)
    device = C.lay_thiet_bi(a.device)
    torch.set_num_threads(4)
    torch.manual_seed(C.SEED)
    if device.type == 'cuda':
        torch.cuda.manual_seed_all(C.SEED)
        torch.cuda.reset_peak_memory_stats()
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    run = a.output_root / 'Checkpoint_BimBom' / run_id
    processed = a.output_root / 'Du_Lieu_Da_Xu_Ly' / run_id
    run.mkdir(parents=True, exist_ok=False)
    latest_path = None
    started = time.perf_counter()
    try:
        if a.resume:
            saved = origin
            stage = saved.get('stage', 'pretrain')
            if a.stage and a.stage != stage:
                raise ValueError('Resume phải giữ giai đoạn; đổi giai đoạn bằng --init-from.')
            tokenizer = tokenizers.Tokenizer.from_str(saved['tokenizer'])
            model = LanguageModel(saved['config']).to(device)
            model.load_state_dict(saved['model'])
            encoded, labels, manifest = saved['data'], saved.get('labels'), saved['manifest']
            settings = dict(saved['settings'])
        else:
            stage, saved, labels = a.stage or 'pretrain', {}, None
            folder = a.folder or ROOT / 'Hoc_BimBom/Du_Lieu_Huan_Luyen' / ('Chat_SFT' if stage == 'sft' else 'Pretrain')
            if origin:
                tokenizer = tokenizers.Tokenizer.from_str(origin['tokenizer'])
                model = LanguageModel(origin['config']).to(device)
                model.load_state_dict(origin['model'])
                if stage == 'sft':
                    encoded, labels, manifest = prepare_sft(folder, tokenizer, processed, C.SEED)
                else:
                    tokenizer, encoded, manifest = prepare(folder, processed, C.VOCAB_SIZE, C.SEED, tokenizer=tokenizer,
                                                            history_folder=ROOT / 'Da_Hoc')
            else:
                if stage == 'sft':
                    raise ValueError('SFT cần --init-from CHECKPOINT của mô hình nền.')
                tokenizer, encoded, manifest = prepare(folder, processed, 512 if a.smoke else C.VOCAB_SIZE, C.SEED)
                config = dict(vocab=tokenizer.get_vocab_size(), context=32 if a.smoke else C.CONTEXT_LENGTH,
                              dim=32 if a.smoke else C.MODEL_DIM, heads=C.MODEL_HEADS, layers=1 if a.smoke else C.MODEL_LAYERS)
                if min(config.values()) < 1 or config['dim'] % config['heads']:
                    raise ValueError('Kiến trúc không hợp lệ.')
                model = LanguageModel(config).to(device)
            settings = dict(batch=1 if a.smoke else C.MICRO_BATCH_SIZE, accum=1 if a.smoke else C.GRAD_ACCUM_STEPS,
                            lr=C.LEARNING_RATE, every=5 if a.smoke else C.CHECKPOINT_EVERY_STEPS,
                            fp16=C.USE_FP16, seed=C.SEED)
        if any(not math.isfinite(settings[k]) or settings[k] <= 0 for k in ('batch', 'accum', 'lr', 'every')):
            raise ValueError('batch/accum/lr/every phải dương, hữu hạn.')
        archive_enabled = not a.smoke and a.output_root.resolve() == (ROOT / 'Ket_Qua').resolve()
        archive_snapshot = snapshot_sources(manifest, stage, ROOT) if archive_enabled else None
        optimizer = torch.optim.AdamW(model.parameters(), lr=settings['lr'])
        amp = settings['fp16'] and device.type == 'cuda'
        scaler = torch.amp.GradScaler('cuda', enabled=amp)
        if saved:
            optimizer.load_state_dict(saved['optimizer'])
            if amp and saved['scaler']:
                scaler.load_state_dict(saved['scaler'])
            torch.set_rng_state(saved['rng'])
            if device.type == 'cuda' and saved['cuda_rng']:
                torch.cuda.set_rng_state_all(saved['cuda_rng'])
        best_info = find_best(a.resume, saved) if saved else None
        best_path, baseline = (best_info[0], best_info[1]) if best_info else (None, float('inf'))
        early = EarlyStopping(limits['patience'], limits['min_delta'], saved.get('early_stopping'), baseline)
        # A historical score may survive deletion of its file; only point best.json at verified weights.
        early.best = baseline
        stats = dict(attempts=step0, skipped_steps=0, consecutive_nonfinite=0, overflow_count=0, invalid_loss_count=0)
        stats.update(saved.get('training_stats', {}))
        if saved and not saved.get('training_stats') and saved['step'] > step0:
            stats.update(attempts=saved['step'], skipped_steps=saved['step']-step0)
        data = {k: torch.tensor(v, dtype=torch.long) for k, v in encoded.items()}
        targets = {k: torch.tensor(v, dtype=torch.long) for k, v in labels.items()} if labels else data
        sampling_indexes = {k: label_positions(data[k], targets[k]) for k in data}
        token_hash = hashlib.sha256(tokenizer.to_str().encode()).hexdigest()
        data_hash = hashlib.sha256(json.dumps(dict(data=encoded, labels=labels), sort_keys=True).encode()).hexdigest()
        metadata = dict(device=str(device), gpu=torch.cuda.get_device_name() if device.type == 'cuda' else None,
                        python=platform.python_version(), torch=str(torch.__version__), tokenizers=tokenizers.__version__,
                        format=2, config=model.config, settings=settings, safety=limits,
                        parameters=sum(p.numel() for p in model.parameters()), resume=str(a.resume) if a.resume else None,
                        init_from=str(a.init_from) if a.init_from else None, dataset=manifest['dataset_sha256'], stage=stage,
                        initial_step=step0, target_step=a.steps, best_checkpoint=str(best_path) if best_path else None)
        atomic_json(run / 'config.json', metadata)
        print(json.dumps(metadata, ensure_ascii=False), flush=True)
        previous_scores = None
        last_grad = None
        step = step0
        eval_every = min(5, limits['eval_every']) if a.smoke else limits['eval_every']

        def record(reason=None, force=False):
            nonlocal best_path, latest_path, previous_scores
            if not finite_state(model, optimizer):
                raise FloatingPointError('Từ chối ghi checkpoint chứa NaN/Inf trong model hoặc optimizer.')
            scores = evaluate_model(model, data, targets, settings['batch'], device, sampling_indexes)
            improved = early.observe(scores['validation_loss'], step)
            if limits['early_stopping'] and early.stopped:
                reason = reason or 'early_stopping'
            overfit = (scores['validation_loss'] > early.best + limits['min_delta']
                       and (scores['validation_loss'] > scores['train_loss'] + 1.0
                            or (previous_scores is not None and scores['train_loss'] < previous_scores['train_loss']
                                and scores['validation_loss'] > previous_scores['validation_loss'])))
            elapsed = time.perf_counter() - started
            rate = (step-step0) / max(elapsed, .001)
            row = dict(step=step, **scores, **stats, learning_rate=optimizer.param_groups[0]['lr'], grad_norm=last_grad,
                       seconds=elapsed, steps_per_second=rate, remaining_steps=max(0, a.steps-step),
                       estimated_remaining_seconds=(a.steps-step)/rate if rate > 0 else None,
                       early_stopping_bad_evals=early.bad_evals, early_stopping_enabled=limits['early_stopping'],
                       overfitting_warning=overfit, stop_reason=reason,
                       peak_vram_bytes=torch.cuda.max_memory_allocated() if device.type == 'cuda' else 0)
            save = force or improved or step % settings['every'] == 0 or step == a.steps or bool(reason)
            if save:
                target = run / f'step_{step:08d}.pt'
                if target.exists():
                    target = run / f'step_{step:08d}_{uuid.uuid4().hex[:8]}.pt'
                candidate_best = target.resolve() if improved or best_path is None else best_path
                state = dict(format=2, model=model.state_dict(), optimizer=optimizer.state_dict(), scaler=scaler.state_dict(),
                             step=step, step_semantics='successful_optimizer_updates', best=early.best,
                             best_checkpoint=str(candidate_best), validation_loss=scores['validation_loss'],
                             early_stopping=early.state_dict(), training_stats=dict(stats), metrics=row,
                             config=model.config, settings=settings, tokenizer=tokenizer.to_str(),
                             data=encoded, labels=labels, manifest=manifest, stage=stage, device=str(device),
                             rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all() if device.type == 'cuda' else [],
                             tokenizer_sha256=token_hash, data_sha256=data_hash)
                temp = target.with_suffix('.tmp')
                try:
                    with temp.open('xb') as handle:
                        torch.save(state, handle)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temp, target)
                finally:
                    temp.unlink(missing_ok=True)
                latest_path, best_path = target, candidate_best
                atomic_json(run / 'latest.json', dict(checkpoint=target.name, **row))
                atomic_json(run / 'best.json', dict(checkpoint=str(best_path), validation_loss=early.best))
                with torch.random.fork_rng(devices=[torch.cuda.current_device()] if device.type == 'cuda' else []):
                    torch.manual_seed(123)
                    sample = generate(model, tokenizer, 'BimBom', 40, .8, device, interruptible=False)
                (run / (target.stem.replace('step_', 'sample_') + '.txt')).write_text(sample, encoding='utf-8')
                model.train()
            append_json(run / 'metrics.jsonl', row)
            append_json(a.output_root / 'Nhat_Ky_Train' / (run_id + '.jsonl'), row)
            atomic_json(run / 'last_metrics.json', row)
            previous_scores = scores
            print(json.dumps(row, ensure_ascii=False), flush=True)
            if overfit:
                print('CẢNH BÁO overfitting: validation xấu hơn mốc tốt nhất; cần xem lại độ đa dạng và cách chia dữ liệu.', flush=True)
            if early.stopped and not limits['early_stopping'] and reason is None:
                print(f'Validation chưa cải thiện đủ trong {early.bad_evals} lần đánh giá. '
                      'Chế độ warn: tiếp tục tới số bước yêu cầu; checkpoint best vẫn được giữ riêng.', flush=True)
            return reason

        reason = record(force=True)
        while step < a.steps and reason is None:
            if should_stop():
                reason = record('user_stop', force=True)
                break
            stats['attempts'] += 1
            result = optimizer_attempt(model, optimizer, scaler,
                                       lambda: training_batch(data['train'], targets['train'], model.context, settings['batch'], device,
                                                              positions_index=sampling_indexes['train']),
                                       settings['accum'], device, amp)
            last_grad = result['grad_norm']
            if result['success']:
                step += 1
                stats['consecutive_nonfinite'] = 0
            else:
                stats['skipped_steps'] += 1
                stats['consecutive_nonfinite'] += 1
                stats['overflow_count'] += int(result['overflow'])
                stats['invalid_loss_count'] += int(result['reason'] == 'nonfinite_loss')
                event = dict(event='skipped_update', step=step, **stats, reason=result['reason'], grad_norm=last_grad,
                             learning_rate=optimizer.param_groups[0]['lr'], amp_scale=scaler.get_scale())
                append_json(run / 'events.jsonl', event)
                append_json(a.output_root / 'Nhat_Ky_Train' / (run_id + '.jsonl'), event)
                print(json.dumps(event), flush=True)
                if stats['consecutive_nonfinite'] >= limits['max_nonfinite']:
                    reason = record('nonfinite_limit', force=True)
                    print('CẢNH BÁO: quá nhiều cập nhật NaN/Inf liên tiếp; đã dừng an toàn.', flush=True)
                    break
            if should_stop():
                reason = record('user_stop', force=True)
            elif result['success'] and (step % eval_every == 0 or step % settings['every'] == 0 or step == a.steps):
                reason = record()
        reason = reason or 'target_reached'
        atomic_json(run / 'completion.json', dict(reason=reason, step=step, target_step=a.steps, **stats,
                                                  early_stopping_enabled=limits['early_stopping'],
                                                  latest_checkpoint=str(latest_path), best_checkpoint=str(best_path)))
        print(f'Kết thúc: {reason}; optimizer steps thành công={step}; bỏ qua={stats["skipped_steps"]}.\nLatest: {latest_path}\nBest: {best_path}', flush=True)
        try:
            archive_completed_inputs(archive_snapshot, ROOT, run, reason, step0, step,
                                     latest_path, enabled=archive_enabled)
        except (OSError, ValueError, RuntimeError) as error:
            print(f'Checkpoint đã lưu, nhưng chưa hoàn tất chuyển tài liệu sang Da_Hoc: {error}. '
                  'Xem archived_sources.json nếu có; các file chưa chuyển vẫn ở vị trí cũ.', flush=True)
        return run
    except BaseException:
        (run / 'error.log').write_text(traceback.format_exc(), encoding='utf-8')
        print(f'Đã dừng do lỗi. Checkpoint hợp lệ cuối cùng của lần này: {latest_path or "chưa có"}. Không lưu trạng thái lỗi.', flush=True)
        raise


def main():
    global _interrupt_requested
    _interrupt_requested = False
    def interrupt(signum, frame):
        global _interrupt_requested
        if _interrupt_requested:
            raise KeyboardInterrupt
        _interrupt_requested = True
        print('\nĐã nhận Ctrl+C. Chờ hoàn tất bước và lưu checkpoint; Ctrl+C lần nữa buộc dừng.', flush=True)
    previous_handler = signal.signal(signal.SIGINT, interrupt)
    try:
        with session_lock(kind='train'):
            train_main()
    except (ValueError, RuntimeError, FloatingPointError, OSError, EOFError) as error:
        raise SystemExit(f'Lỗi: {error}') from error
    except KeyboardInterrupt:
        raise SystemExit('Đã buộc dừng; dùng checkpoint hoàn chỉnh gần nhất.')
    finally:
        signal.signal(signal.SIGINT, previous_handler)


if __name__ == '__main__':
    main()
