"""Huấn luyện BimBom v2 từ đầu hoặc tiếp tục checkpoint."""
import argparse
import json
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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder', type=Path, default=ROOT / 'Hoc_BimBom')
    p.add_argument('--steps', type=int, default=600, help='Tổng optimizer steps cần đạt')
    p.add_argument('--resume', type=Path)
    p.add_argument('--include-approved', action='store_true')
    p.add_argument('--device', choices=['cpu', 'cuda', 'auto'])
    p.add_argument('--smoke', action='store_true', help='Mô hình nhỏ để kiểm tra pipeline')
    a = p.parse_args()
    if a.steps < 1:
        p.error('steps > 0')
    device = C.lay_thiet_bi(a.device)
    torch.set_num_threads(4)
    torch.manual_seed(C.SEED)
    if device.type == 'cuda':
        torch.cuda.manual_seed_all(C.SEED)
        torch.cuda.reset_peak_memory_stats()
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    run = ROOT / 'Ket_Qua/Checkpoint_BimBom' / run_id
    run.mkdir(parents=True, exist_ok=False)
    start_time = time.perf_counter()
    try:
        if a.resume:
            if a.smoke or a.include_approved:
                p.error('Resume dùng dữ liệu/cấu hình đã lưu; không kết hợp smoke/include-approved.')
            model, tokenizer, saved = load_model(a.resume, device)
            encoded, manifest = saved['data'], saved['manifest']
            settings = saved['settings']
            step0 = saved['step']
            if a.steps <= step0:
                raise ValueError(f'--steps phải lớn hơn step đã lưu ({step0}).')
        else:
            tokenizer, encoded, manifest = prepare(a.folder, ROOT / 'Ket_Qua/Du_Lieu_Da_Xu_Ly' / run_id,
                                                    512 if a.smoke else C.VOCAB_SIZE, C.SEED, a.include_approved)
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
        def batch(source, generator=None):
            length = min(model.context, len(source) - 1)
            positions = torch.randint(len(source) - length, (settings['batch'],), generator=generator)
            return (torch.stack([source[i:i+length] for i in positions]).to(device),
                    torch.stack([source[i+1:i+length+1] for i in positions]).to(device))
        @torch.no_grad()
        def evaluate():
            model.eval()
            result = {}
            for name, source in data.items():
                gen = torch.Generator().manual_seed(123)
                losses = []
                for _ in range(5):
                    x, y = batch(source, gen)
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
                        resume=str(a.resume) if a.resume else None, dataset=manifest['dataset_sha256'])
        (run / 'config.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        print(json.dumps(metadata), flush=True)
        best = saved.get('best', float('inf'))
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
            state = dict(format=2, model=model.state_dict(), optimizer=optimizer.state_dict(),
                         scaler=scaler.state_dict(), step=step, best=best, config=model.config,
                         settings=settings, tokenizer=tokenizer.to_str(), data=encoded, manifest=manifest,
                         rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all() if device.type == 'cuda' else [])
            target = run / f'step_{step:08d}.pt'
            temporary = target.with_suffix('.tmp')
            torch.save(state, temporary)
            temporary.replace(target)
            if improved:
                (run / 'best.json').write_text(json.dumps({'checkpoint': target.name, **row}), encoding='utf-8')
            with torch.random.fork_rng(devices=[torch.cuda.current_device()] if device.type == 'cuda' else []):
                torch.manual_seed(123)
                sample = generate(model, tokenizer, 'BimBom', 40, .8, device)
            (run / f'sample_{step:08d}.txt').write_text(sample, encoding='utf-8')
            model.train()
            print(json.dumps(row), flush=True)
        record(step0)
        for step in range(step0 + 1, a.steps + 1):
            optimizer.zero_grad(set_to_none=True)
            for _ in range(settings['accum']):
                x, y = batch(data['train'])
                with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=amp):
                    loss = F.cross_entropy(model(x).flatten(0, 1), y.flatten()) / settings['accum']
                if not torch.isfinite(loss):
                    raise RuntimeError('Loss NaN/Inf; thử USE_FP16=False hoặc giảm learning rate.')
                scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
            scaler.step(optimizer)
            scaler.update()
            if step % settings['every'] == 0 or step == a.steps:
                record(step)
        print(f'Hoàn tất: {run}', flush=True)
    except BaseException:
        (run / 'error.log').write_text(traceback.format_exc(), encoding='utf-8')
        raise


if __name__ == '__main__':
    main()


