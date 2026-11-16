"""BimBom v2: document split, byte BPE tokenizer, causal Transformer."""
import hashlib
import json
import random
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
    result, seen = [], set()
    for path in sorted(Path(folder).rglob('*')):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in {'.txt', '.md'}:
            continue
        text = unicodedata.normalize('NFC', path.read_text(encoding='utf-8-sig')).strip()
        sha = hashlib.sha256(text.encode()).hexdigest()
        if text and sha not in seen:
            result.append(dict(source=str(path.resolve()), text=text, sha256=sha))
            seen.add(sha)
    if approved:
        from Model_BimBomAI.ky_nang import training_documents
        for source, text in training_documents():
            sha = hashlib.sha256(text.encode()).hexdigest()
            if sha not in seen:
                result.append(dict(source=source, text=text, sha256=sha))
                seen.add(sha)
    return result


def prepare(folder, output, vocab, seed, approved=False):
    docs = documents(folder, approved)
    if len(docs) < 2:
        raise ValueError('Cần ít nhất 2 tài liệu khác nhau để tách train/validation theo tài liệu.')
    random.Random(seed).shuffle(docs)
    n = max(1, round(len(docs) * .15))
    valid, train = docs[:n], docs[n:]
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
        if len(encoded[name]) < 3:
            raise ValueError(f'Tập {name} quá ngắn.')
    manifest = {name: [{k: v for k, v in d.items() if k != 'text'} for d in group]
                for name, group in [('train', train), ('validation', valid)]}
    manifest['seed'] = seed
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
def generate(model, tokenizer, prompt, count, temperature, device):
    if count < 0 or temperature <= 0:
        raise ValueError('tokens >= 0 và temperature > 0')
    model.eval()
    ids = tokenizer.encode(prompt).ids or [tokenizer.token_to_id('[EOS]')]
    for _ in range(count):
        logits = model(torch.tensor([ids[-model.context:]], device=device))[0, -1].float()
        token = torch.multinomial((logits / temperature).softmax(-1), 1).item()
        if token == tokenizer.token_to_id('[EOS]'):
            break
        ids.append(token)
    return tokenizer.decode(ids)


def load_model(path, device):
    saved = torch.load(path, map_location='cpu', weights_only=True)
    if saved.get('format') != 2:
        raise ValueError('Checkpoint cũ không tương thích v2. Hãy huấn luyện mới bằng train.py.')
    model = LanguageModel(saved['config']).to(device)
    model.load_state_dict(saved['model'])
    return model, Tokenizer.from_str(saved['tokenizer']), saved


