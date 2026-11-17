"""BimBom v2: document split, byte BPE tokenizer, causal Transformer."""
import hashlib
import json
import random
import re
import sys
import unicodedata
from pathlib import Path
import torch
from torch import nn
from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders

if sys.version_info[:2] != (3, 13):
    raise RuntimeError('BimBom AI yêu cầu Python 3.13 trong Model_BimBomAI/.venv.')

ROOT = Path(__file__).resolve().parent.parent


def documents(folder, approved=False):
    folder = Path(folder).resolve()
    learning = (ROOT / 'Hoc_BimBom').resolve()
    if folder == learning:
        folder = learning / 'Du_Lieu_Huan_Luyen/Pretrain'
    blocked = [learning / name for name in ('Tai_Lieu', 'Hoi_Thoai_Goc', 'Cho_Duyet', 'Du_Lieu_Huan_Luyen/Chat_SFT')]
    if any(folder == p or p in folder.parents for p in blocked):
        raise ValueError('Thư mục này chưa được chọn cho Pretrain. Chuyển văn bản đã kiểm tra vào Du_Lieu_Huan_Luyen/Pretrain.')
    if approved:
        raise ValueError('Không trộn hội thoại vào Pretrain. Dùng train --stage sft --init-from CHECKPOINT.')
    result, seen = [], set()
    for path in sorted(Path(folder).rglob('*')):
        resolved = path.resolve()
        if any(resolved == p or p in resolved.parents for p in blocked):
            continue
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in {'.txt', '.md'}:
            continue
        text = unicodedata.normalize('NFC', path.read_text(encoding='utf-8-sig')).strip()
        sha = hashlib.sha256(text.encode()).hexdigest()
        if text and sha not in seen:
            result.append(dict(source=str(path.resolve()), text=text, sha256=sha))
            seen.add(sha)
    return result


def prepare(folder, output, vocab, seed, approved=False, tokenizer=None):
    docs = documents(folder, approved)
    if not docs:
        raise ValueError('Cần ít nhất 1 tài liệu TXT/MD có nội dung để huấn luyện.')
    if len(docs) == 1:
        doc = docs[0]
        text = doc['text']
        if len(text) < 2:
            raise ValueError('Tài liệu quá ngắn để tách train/validation; hãy bổ sung nội dung.')
        target = max(1, min(len(text) - 1, round(len(text) * .85)))
        # Prefer a word boundary, keeping the final section out of tokenizer training.
        boundaries = [m.start() for m in re.finditer(r'\s+', text)]
        cut = min(boundaries, key=lambda i: abs(i - target)) if boundaries else target
        parts = []
        for start, end in [(0, cut), (cut, len(text))]:
            part = text[start:end]
            parts.append(dict(source=doc['source'], text=part,
                              sha256=hashlib.sha256(part.encode()).hexdigest(),
                              source_sha256=doc['sha256'], char_start=start, char_end=end))
        train, valid = [parts[0]], [parts[1]]
    else:
        random.Random(seed).shuffle(docs)
        n = max(1, round(len(docs) * .15))
        valid, train = docs[:n], docs[n:]
    if tokenizer is None:
        tokenizer = Tokenizer(models.BPE(unk_token='[UNK]'))
        tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
        tokenizer.decoder = decoders.ByteLevel()
        tokenizer.train_from_iterator((d['text'] for d in train), trainers.BpeTrainer(
            vocab_size=vocab, special_tokens=['[UNK]', '[EOS]'],
            initial_alphabet=pre_tokenizers.ByteLevel.alphabet(), show_progress=False))
    eos = tokenizer.token_to_id('[EOS]')
    encoded = {}
    for name, group in [('train', train), ('validation', valid)]:
        encoded[name] = [token for d in group for token in tokenizer.encode(d['text']).ids + [eos]]
        if len(encoded[name]) < 2:
            raise ValueError(f'Tập {name} quá ngắn.')
    manifest = {name: [{k: v for k, v in d.items() if k != 'text'} for d in group]
                for name, group in [('train', train), ('validation', valid)]}
    manifest['seed'] = seed
    manifest['split_strategy'] = 'single_document_text' if len(docs) == 1 else 'document'
    manifest['dataset_sha256'] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    output.mkdir(parents=True, exist_ok=False)
    tokenizer.save(str(output / 'tokenizer.json'))
    (output / 'tokens.json').write_text(json.dumps(encoded), encoding='utf-8')
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return tokenizer, encoded, manifest


class LanguageModel(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.context = config['context']
        self.token = nn.Embedding(config['vocab'], config['dim'])
        self.position = nn.Embedding(self.context, config['dim'])
        self.blocks = nn.ModuleList([nn.TransformerEncoderLayer(
            config['dim'], config['heads'], config['dim'] * 4, dropout=.1,
            batch_first=True, norm_first=True) for _ in range(config['layers'])])
        self.norm = nn.LayerNorm(config['dim'])
        self.head = nn.Linear(config['dim'], config['vocab'], bias=False)
        self.head.weight = self.token.weight
        # Small embeddings avoid saturated logits when the output weights are tied.
        nn.init.normal_(self.token.weight, std=.02)
        nn.init.normal_(self.position.weight, std=.02)

    def forward(self, tokens):
        length = tokens.shape[1]
        x = self.token(tokens) + self.position(torch.arange(length, device=tokens.device))
        mask = torch.triu(torch.ones(length, length, dtype=torch.bool, device=tokens.device), diagonal=1)
        for block in self.blocks:
            x = block(x, src_mask=mask)
        return self.head(self.norm(x))


@torch.no_grad()
def generate(model, tokenizer, prompt, count, temperature, device, interruptible=True):
    if count < 0 or temperature <= 0:
        raise ValueError('tokens >= 0 và temperature > 0')
    model.eval()
    ids = tokenizer.encode(prompt).ids or [tokenizer.token_to_id('[EOS]')]
    for _ in range(count):
        if interruptible:
            from Model_BimBomAI.Ma_Nguon.runtime import check_stop
            check_stop()
        logits = model(torch.tensor([ids[-model.context:]], device=device))[0, -1].float()
        token = torch.multinomial((logits / temperature).softmax(-1), 1).item()
        if token == tokenizer.token_to_id('[EOS]'):
            break
        ids.append(token)
    return tokenizer.decode(ids)


def load_model(path, device):
    from Model_BimBomAI.Ma_Nguon.checkpoint import validate
    saved = validate(path, resume=False)
    model = LanguageModel(saved['config']).to(device)
    model.load_state_dict(saved['model'])
    return model, Tokenizer.from_str(saved['tokenizer']), saved


