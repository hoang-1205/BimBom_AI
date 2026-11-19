"""Reviewed chat pairs use a fixed tokenizer and answer-only loss."""
import hashlib
import json
import random
from .memory import read_approved
from .runtime import atomic_json
from .duplicates import normalized


def prepare_sft(folder, tokenizer, output, seed):
    entries, seen = [], set()
    for path in sorted(folder.glob('*.json')):
        entry = read_approved(path)
        key = (normalized(entry['question']).casefold(), normalized(entry['answer']))
        if key not in seen:
            entries.append((path, entry))
            seen.add(key)
    by_question = {}
    for path, entry in entries:
        by_question.setdefault(normalized(entry['question']).casefold(), []).append((path, entry))
    groups = list(by_question.values())
    if len(groups) < 2:
        raise ValueError('SFT cần ít nhất 2 câu hỏi khác nhau đã duyệt để tách train/validation; nhiều đáp án cho một câu hỏi chưa đủ.')
    random.Random(seed).shuffle(groups)
    n = max(1, round(len(groups) * .15))
    encoded, labels, manifest = {}, {}, dict(seed=seed, split_strategy='reviewed_question_groups', stage='sft')
    for split, selected in [('train', groups[n:]), ('validation', groups[:n])]:
        rows = [pair for group in selected for pair in group]
        ids, targets, sources = [], [], []
        for path, entry in rows:
            prompt = tokenizer.encode('Câu hỏi: ' + entry['question'] + '\nTrả lời:').ids
            reply = tokenizer.encode(' ' + entry['answer']).ids + [tokenizer.token_to_id('[EOS]')]
            ids.extend(prompt + reply)
            targets.extend([-100] * len(prompt) + reply)
            sources.append(dict(source=str(path.resolve()), sha256=entry['reviewed_sha256']))
        encoded[split], labels[split], manifest[split] = ids, targets, sources
    manifest['dataset_sha256'] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    output.mkdir(parents=True, exist_ok=False)
    tokenizer.save(str(output / 'tokenizer.json'))
    atomic_json(output / 'tokens.json', encoded)
    atomic_json(output / 'labels.json', labels)
    atomic_json(output / 'manifest.json', manifest)
    return encoded, labels, manifest


def label_positions(source, targets):
    """Build the SFT sampling index once; pretraining needs no corpus scan."""
    import torch
    if source is targets:
        return None
    valid = torch.nonzero(targets[1:] != -100).flatten() + 1
    if not len(valid):
        raise ValueError('Không có token đích hợp lệ.')
    return valid if len(valid) != len(targets)-1 or targets[0].item() == -100 else None


_AUTO_POSITIONS = object()


def training_batch(source, targets, context, batch_size, device, generator=None, positions_index=_AUTO_POSITIONS):
    import torch
    length = min(context, len(source) - 1)
    # Choose a target token, then a window containing it. No all-ignored SFT batches.
    if length < 1 or len(targets) != len(source) or batch_size < 1:
        raise ValueError('Dữ liệu lấy mẫu cần ít nhất 2 token, nhãn cùng độ dài và batch dương.')
    valid = label_positions(source, targets) if positions_index is _AUTO_POSITIONS else positions_index
    if valid is not None:
        chosen = valid[torch.randint(len(valid), (batch_size,), generator=generator)]
        offsets = torch.randint(length, (batch_size,), generator=generator) + 1
        positions = (chosen - offsets).clamp(0, len(source) - length - 1)
    else:
        positions = torch.randint(len(source) - length, (batch_size,), generator=generator)
    return (torch.stack([source[i:i+length] for i in positions]).to(device),
            torch.stack([targets[i+1:i+length+1] for i in positions]).to(device))
