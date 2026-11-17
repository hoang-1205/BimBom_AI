"""Huấn luyện BimBom v2 từ đầu hoặc tiếp tục checkpoint."""
import argparse
import json
import hashlib
import math
import platform
import time
import traceback
from datetime import datetime
from pathlib import Path
import torch
import tokenizers
import torch.nn.functional as F
import Chinh_Che_Do as C
from Model_BimBomAI.pipeline import ROOT, LanguageModel, prepare, load_model, generate
from Model_BimBomAI.Ma_Nguon.checkpoint import validate
from Model_BimBomAI.Ma_Nguon.data import prepare_sft, training_batch
from Model_BimBomAI.Ma_Nguon.runtime import session_lock, atomic_json, append_json, stop_requested


def train_main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder', type=Path)
    p.add_argument('--steps', type=int, default=600, help='Tổng optimizer steps cần đạt')
    checkpoints = p.add_mutually_exclusive_group()
    checkpoints.add_argument('--resume', type=Path)
    checkpoints.add_argument('--init-from', type=Path, help='Giữ trọng số/tokenizer, học dữ liệu mới với optimizer mới')
    p.add_argument('--stage', choices=['pretrain', 'sft'])
    p.add_argument('--output-root', type=Path, default=ROOT / 'Ket_Qua', help='Thư mục kết quả; dùng thư mục tạm khi kiểm thử')
    p.add_argument('--include-approved', action='store_true')
    p.add_argument('--device', choices=['cpu', 'cuda', 'auto'])
    p.add_argument('--smoke', action='store_true', help='Mô hình nhỏ để kiểm tra pipeline')
    a = p.parse_args()
    if a.steps < 1:
        p.error('steps > 0')
    if a.include_approved:
        p.error('Không trộn dữ liệu: dùng --stage sft --init-from CHECKPOINT với các cặp đã duyệt.')
    if a.resume and a.smoke:
        p.error('Resume dùng cấu hình đã lưu; không kết hợp --smoke.')
    if a.resume and a.folder:
        print('Lưu ý: --folder được bỏ qua khi resume; dùng đúng dữ liệu đã lưu trong checkpoint.', flush=True)
    if a.init_from and a.smoke:
        p.error('--init-from dùng kiến trúc đã lưu; không kết hợp --smoke.')
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
    start_time = time.perf_counter()
    try:
        if a.resume:
            validate(a.resume, resume=True)
            model, tokenizer, saved = load_model(a.resume, device)
            encoded, manifest = saved['data'], saved['manifest']
            labels = saved.get('labels')
            stage = saved.get('stage', 'pretrain')
            if a.stage and a.stage != stage:
                raise ValueError('Resume phải giữ giai đoạn đã lưu. Đổi dữ liệu/giai đoạn bằng --init-from.')
            settings = saved['settings']
            step0 = saved['step']
            if a.steps <= step0:
                raise ValueError(f'--steps phải lớn hơn step đã lưu ({step0}).')
        else:
            stage = a.stage or 'pretrain'
            folder = a.folder or ROOT / 'Hoc_BimBom/Du_Lieu_Huan_Luyen' / ('Chat_SFT' if stage == 'sft' else 'Pretrain')
            labels = None
            if a.init_from:
                model, tokenizer, _ = load_model(a.init_from, device)
                if stage == 'sft':
                    encoded, labels, manifest = prepare_sft(folder, tokenizer, processed, C.SEED)
                else:
                    tokenizer, encoded, manifest = prepare(folder, processed, C.VOCAB_SIZE, C.SEED, tokenizer=tokenizer)
            else:
                if stage == 'sft':
                    raise ValueError('SFT cần mô hình nền: dùng --init-from CHECKPOINT sau Pretrain.')
                tokenizer, encoded, manifest = prepare(folder, processed, 512 if a.smoke else C.VOCAB_SIZE, C.SEED)
                config = dict(vocab=tokenizer.get_vocab_size(), context=32 if a.smoke else C.CONTEXT_LENGTH,
                              dim=32 if a.smoke else C.MODEL_DIM, heads=C.MODEL_HEADS,
                              layers=1 if a.smoke else C.MODEL_LAYERS)
                if config['dim'] % config['heads'] or min(config.values()) < 1:
                    raise ValueError('Cấu hình mô hình không hợp lệ; dim phải chia hết heads.')
                model = LanguageModel(config).to(device)
            settings = dict(batch=1 if a.smoke else C.MICRO_BATCH_SIZE,
                            accum=1 if a.smoke else C.GRAD_ACCUM_STEPS,
                            lr=C.LEARNING_RATE, every=5 if a.smoke else C.CHECKPOINT_EVERY_STEPS,
                            fp16=C.USE_FP16, seed=C.SEED)
            saved, step0 = {}, 0
        if min(settings['batch'], settings['accum'], settings['every'], settings['lr']) <= 0:
            raise ValueError('batch/accum/every/lr phải dương')
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
        data = {k: torch.tensor(v, dtype=torch.long) for k, v in encoded.items()}
        targets = {k: torch.tensor(v, dtype=torch.long) for k, v in (labels or encoded).items()}
        def batch(name, generator=None):
            return training_batch(data[name], targets[name], model.context, settings['batch'], device, generator)
        @torch.no_grad()
        def evaluate():
            model.eval()
            result = {}
            for name, source in data.items():
                gen = torch.Generator().manual_seed(123)
                losses = []
                for _ in range(5):
                    x, y = batch(name, gen)
                    losses.append(F.cross_entropy(model(x).flatten(0, 1), y.flatten()).item())
                result[name + '_loss'] = sum(losses) / len(losses)
            if not all(math.isfinite(v) for v in result.values()):
                raise RuntimeError('Evaluation loss không hữu hạn')
            result['perplexity'] = math.exp(min(result['validation_loss'], 80))
            model.train()
            return result
        metadata = dict(device=str(device), gpu=torch.cuda.get_device_name() if device.type == 'cuda' else None,
                        python=platform.python_version(), torch=str(torch.__version__),
                        tokenizers=tokenizers.__version__, format=2, config=model.config,
                        settings=settings, parameters=sum(p.numel() for p in model.parameters()),
                        resume=str(a.resume) if a.resume else None, dataset=manifest['dataset_sha256'],
                        stage=stage, init_from=str(a.init_from) if a.init_from else None)
        (run / 'config.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        print(json.dumps(metadata), flush=True)
        best = float('inf')  # best within this run; previous runs remain intact
        def record(step):
            nonlocal best
            scores = evaluate()
            improved = scores['validation_loss'] < best
            best = min(best, scores['validation_loss'])
            elapsed = time.perf_counter() - start_time
            row = dict(step=step, **scores, seconds=elapsed,
                       steps_per_second=(step-step0)/max(elapsed, .001),
                       peak_vram_bytes=torch.cuda.max_memory_allocated() if device.type == 'cuda' else 0)
            with (run / 'metrics.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(row) + '\n')
            append_json(a.output_root / 'Nhat_Ky_Train' / (run_id + '.jsonl'), row)
            state = dict(format=2, model=model.state_dict(), optimizer=optimizer.state_dict(),
                         scaler=scaler.state_dict(), step=step, best=best, config=model.config,
                         settings=settings, tokenizer=tokenizer.to_str(), data=encoded, manifest=manifest,
                         rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all() if device.type == 'cuda' else [],
                         stage=stage, labels=labels, device=str(device),
                         tokenizer_sha256=hashlib.sha256(tokenizer.to_str().encode()).hexdigest(),
                         data_sha256=hashlib.sha256(json.dumps(dict(data=encoded, labels=labels), sort_keys=True).encode()).hexdigest())
            target = run / f'step_{step:08d}.pt'
            temporary = target.with_suffix('.tmp')
            torch.save(state, temporary)
            temporary.replace(target)
            if improved:
                atomic_json(run / 'best.json', {'checkpoint': target.name, **row})
            atomic_json(run / 'latest.json', {'checkpoint': target.name, **row})
            with torch.random.fork_rng(devices=[torch.cuda.current_device()] if device.type == 'cuda' else []):
                torch.manual_seed(123)
                sample = generate(model, tokenizer, 'BimBom', 40, .8, device, interruptible=False)
            (run / f'sample_{step:08d}.txt').write_text(sample, encoding='utf-8')
            model.train()
            print(json.dumps(row), flush=True)
        record(step0)
        if stop_requested():
            print(f'Đã dừng trước bước mới; checkpoint đã lưu: {run}', flush=True)
            return
        for step in range(step0 + 1, a.steps + 1):
            optimizer.zero_grad(set_to_none=True)
            for _ in range(settings['accum']):
                x, y = batch('train')
                with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=amp):
                    loss = F.cross_entropy(model(x).flatten(0, 1), y.flatten()) / settings['accum']
                if not torch.isfinite(loss):
                    raise RuntimeError('Loss NaN/Inf; thử USE_FP16=False hoặc giảm learning rate.')
                scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
            scaler.step(optimizer)
            scaler.update()
            stopping = stop_requested()
            if stopping or step % settings['every'] == 0 or step == a.steps:
                record(step)
            if stopping:
                print(f'Đã lưu checkpoint bước {step} và dừng theo yêu cầu: {run}', flush=True)
                return
        print(f'Hoàn tất: {run}', flush=True)
    except BaseException:
        (run / 'error.log').write_text(traceback.format_exc(), encoding='utf-8')
        raise


def main():
    try:
        with session_lock(kind='train'):
            train_main()
    except (ValueError, RuntimeError, OSError) as error:
        raise SystemExit(f'Lỗi: {error}') from error


if __name__ == '__main__':
    main()


