"""Reviewed chat pairs use a fixed tokenizer and answer-only loss."""
import hashlib
import json
import random
from .memory import read_approved
from .runtime import atomic_json


def prepare_sft(folder, tokenizer, output, seed):
    entries, seen = [], set()
    for path in sorted(folder.glob('*.json')):
        entry = read_approved(path)
        key = (entry['question'], entry['answer'])
        if key not in seen:
            entries.append((path, entry))
            seen.add(key)
    if len(entries) < 2:
        raise ValueError('SFT cần ít nhất 2 cặp hỏi/đáp khác nhau đã duyệt để tách train/validation.')
    random.Random(seed).shuffle(entries)
    n = max(1, round(len(entries) * .15))
    encoded, labels, manifest = {}, {}, dict(seed=seed, split_strategy='reviewed_chat_pairs', stage='sft')
    for split, rows in [('train', entries[n:]), ('validation', entries[:n])]:
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


def training_batch(source, targets, context, batch_size, device, generator=None):
    import torch
    length = min(context, len(source) - 1)
    # Choose a target token, then a window containing it. No all-ignored SFT batches.
    valid = torch.nonzero(targets[1:] != -100).flatten() + 1
    if not len(valid):
        raise ValueError('Không có token đích hợp lệ.')
    if bool((targets == -100).any()):
        chosen = valid[torch.randint(len(valid), (batch_size,), generator=generator)]
        offsets = torch.randint(length, (batch_size,), generator=generator) + 1
        positions = (chosen - offsets).clamp(0, len(source) - length - 1)
    else:
        positions = torch.randint(len(source) - length, (batch_size,), generator=generator)
    return (torch.stack([source[i:i+length] for i in positions]).to(device),
            torch.stack([targets[i+1:i+length+1] for i in positions]).to(device))
