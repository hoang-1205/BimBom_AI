"""Validate checkpoint contents before selecting or loading them."""
import hashlib
import json
import math
from pathlib import Path
import torch
from tokenizers import Tokenizer
from .runtime import ROOT


def _validate(path, expected=None, resume=True):
    from Model_BimBomAI.pipeline import LanguageModel
    saved = torch.load(path, map_location='cpu', weights_only=True)
    if not isinstance(saved, dict) or saved.get('format') != 2:
        raise ValueError('Checkpoint không đúng định dạng v2.')
    config = saved['config']
    if any(type(config.get(k)) is not int or config[k] < 1 for k in ('vocab', 'context', 'dim', 'heads', 'layers')):
        raise ValueError('Kiến trúc không hợp lệ.')
    if config['dim'] % config['heads']:
        raise ValueError('dim phải chia hết heads.')
    if expected and any(config[k] != v for k, v in expected.items()):
        raise ValueError('Kiến trúc khác Chinh_Che_Do.py; khôi phục cấu hình phù hợp hoặc dùng --new.')
    tokenizer = Tokenizer.from_str(saved['tokenizer'])
    if tokenizer.get_vocab_size() != config['vocab'] or tokenizer.token_to_id('[EOS]') is None:
        raise ValueError('Tokenizer không khớp mô hình.')
    token_hash = hashlib.sha256(saved['tokenizer'].encode()).hexdigest()
    if saved.get('tokenizer_sha256', token_hash) != token_hash:
        raise ValueError('Tokenizer bị thay đổi.')
    if type(saved['step']) is not int or saved['step'] < 0:
        raise ValueError('Thiếu số bước hợp lệ.')
    # Validation must not alter the caller's RNG, including exact resume tests.
    with torch.random.fork_rng(devices=[]):
        model = LanguageModel(config)
    if not torch.equal(saved['model']['head.weight'], saved['model']['token.weight']):
        raise ValueError('Trọng số embedding và đầu ra liên kết không khớp.')
    model.load_state_dict(saved['model'], strict=True)
    if any(not torch.isfinite(t).all() for t in model.state_dict().values()):
        raise ValueError('Trọng số có NaN/Inf.')
    if resume:
        settings = saved['settings']
        if any(type(settings[k]) is not int for k in ('batch', 'accum', 'every', 'seed')) or type(settings['fp16']) is not bool:
            raise ValueError('Kiểu dữ liệu cấu hình huấn luyện không hợp lệ.')
        if any(not math.isfinite(settings[k]) or settings[k] <= 0 for k in ('batch', 'accum', 'lr', 'every')):
            raise ValueError('Thông số huấn luyện không hợp lệ.')
        optimizer = torch.optim.AdamW(model.parameters(), lr=settings['lr'])
        optimizer.load_state_dict(saved['optimizer'])
        for parameter, state in optimizer.state.items():
            for key in ('exp_avg', 'exp_avg_sq'):
                if saved['step'] > 0 and key not in state:
                    raise ValueError('Thiếu trạng thái optimizer.')
                if key in state and (state[key].shape != parameter.shape or not torch.isfinite(state[key]).all()):
                    raise ValueError('Trạng thái optimizer không tương thích.')
            if saved['step'] > 0 and ('step' not in state or not torch.isfinite(state['step']).all()):
                raise ValueError('Thiếu bước optimizer hợp lệ.')
        if saved['step'] > 0 and len(optimizer.state) != len(list(model.parameters())):
            raise ValueError('Optimizer chưa lưu đủ tham số.')
        for split in ('train', 'validation'):
            ids = saved['data'][split]
            if len(ids) < 2 or any(type(i) is not int or not 0 <= i < config['vocab'] for i in ids):
                raise ValueError('Token dữ liệu không hợp lệ.')
            if saved.get('labels'):
                labels = saved['labels'][split]
                if (len(labels) != len(ids) or not any(x != -100 for x in labels[1:])
                        or any(x != -100 and x != i for x, i in zip(labels, ids))):
                    raise ValueError('Nhãn SFT không hợp lệ.')
        manifest = dict(saved['manifest'])
        fingerprint = manifest.pop('dataset_sha256')
        if hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest() != fingerprint:
            raise ValueError('Manifest dữ liệu bị thay đổi.')
        if saved.get('data_sha256'):
            body = dict(data=saved['data'], labels=saved.get('labels'))
            if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != saved['data_sha256']:
                raise ValueError('Nội dung token/nhãn dữ liệu bị thay đổi.')
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(saved['rng'])
        if not isinstance(saved['cuda_rng'], list) or not isinstance(saved['scaler'], dict):
            raise ValueError('Thiếu trạng thái RNG/scaler.')
        if any(not isinstance(rng, torch.Tensor) or rng.dtype != torch.uint8 or rng.ndim != 1 or not rng.numel()
               for rng in saved['cuda_rng']):
            raise ValueError('Trạng thái CUDA RNG không hợp lệ.')
        if settings['fp16'] and saved['cuda_rng']:
            scaler = saved['scaler']
            for key in ('scale', 'growth_factor', 'backoff_factor', 'growth_interval', '_growth_tracker'):
                if key not in scaler or not math.isfinite(scaler[key]) or scaler[key] < 0:
                    raise ValueError('Trạng thái AMP scaler không hợp lệ.')
            if scaler['scale'] <= 0 or scaler['growth_factor'] <= 1 or not 0 < scaler['backoff_factor'] < 1:
                raise ValueError('Thông số AMP scaler không hợp lệ.')
        if saved.get('stage', 'pretrain') == 'sft' and not saved.get('labels'):
            raise ValueError('Checkpoint SFT thiếu nhãn câu trả lời.')
    return saved


def validate(path, expected=None, resume=True):
    try:
        return _validate(path, expected, resume)
    except Exception as error:
        raise ValueError(f'Checkpoint không dùng được ({path}): {error}') from error


def discover(folder=None, expected=None, resume=True, stage=None):
    folder = Path(folder) if folder else ROOT / 'Ket_Qua/Checkpoint_BimBom'
    candidates = sorted(folder.rglob('*.pt'), key=lambda p: (p.stat().st_mtime_ns, str(p)), reverse=True)
    skipped = []
    for path in candidates:
        try:
            saved = validate(path, expected, resume)
            if stage is not None and saved.get('stage', 'pretrain') != stage:
                raise ValueError(f'Khác giai đoạn {stage}.')
            return path, saved, skipped
        except Exception as error:
            skipped.append((str(path), str(error)))
    return None, None, skipped
