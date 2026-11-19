"""BimBom v2: document split, byte BPE tokenizer, causal Transformer."""
import hashlib
import json
import math
import random
import re
import sys
import unicodedata
from pathlib import Path
import torch
from torch import nn
from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders
import Chinh_Che_Do as C
from Model_BimBomAI.Ma_Nguon.document_reader import extract_document, supported_path
from Model_BimBomAI.Ma_Nguon.duplicates import DuplicateReport, historical_index, filter_history, unique_training_lines
from Model_BimBomAI.Ma_Nguon.inference import sample_token
from Model_BimBomAI.Ma_Nguon.auto_split import needs_split, split_queue, record_history_skips

if sys.version_info[:2] != (3, 13):
    raise RuntimeError('BimBom AI yêu cầu Python 3.13 trong Model_BimBomAI/.venv.')

ROOT = Path(__file__).resolve().parent.parent


def documents(folder, approved=False, duplicate_report=None, auto_split=False):
    folder = Path(folder).resolve()
    learning = (ROOT / 'Hoc_BimBom').resolve()
    if folder == learning:
        folder = learning / 'Du_Lieu_Huan_Luyen/Pretrain'
    blocked = [learning / name for name in ('Tai_Lieu', 'Hoi_Thoai_Goc', 'Cho_Duyet', 'Du_Lieu_Huan_Luyen/Chat_SFT')]
    blocked.append((ROOT / 'Da_Hoc').resolve())
    blocked.append((ROOT / 'Hoc_BimBom/Da_Chia').resolve())
    if any(folder == p or p in folder.parents for p in blocked):
        raise ValueError('Thư mục này chưa được chọn cho Pretrain. Chuyển văn bản đã kiểm tra vào Du_Lieu_Huan_Luyen/Pretrain.')
    if approved:
        raise ValueError('Không trộn hội thoại vào Pretrain. Dùng train --stage sft --init-from CHECKPOINT.')
    for name in ('IMPORT_MAX_TOTAL_FILE_MB', 'IMPORT_MAX_TOTAL_CHARACTERS'):
        if type(getattr(C, name)) is not int or getattr(C, name) < 1:
            raise ValueError(f'{name} phải là số nguyên dương.')
    result, seen, candidates = [], {}, []
    total_bytes = total_characters = 0
    def skipped(path, reason):
        message = f'{path}: {reason}'
        print('[Tạm bỏ qua tài liệu] ' + message, file=sys.stderr)
        if duplicate_report is not None:
            duplicate_report.notes.append('File chưa nhập: ' + message)
    for path in Path(folder).rglob('*'):
        resolved = path.resolve()
        if any(resolved == p or p in resolved.parents for p in blocked):
            continue
        if (not path.is_file() or path.is_symlink() or path.name.startswith('~$')
                or not supported_path(path)):
            continue
        try:
            size = path.stat().st_size
            if needs_split(path, size):
                if not auto_split:
                    skipped(path, 'file lớn sẽ tự chia khi chọn tạo mới/học dữ liệu mới; status và resume không tạo phần mới')
                    continue
                for part, info in split_queue(path, ROOT):
                    candidates.append((part.stat().st_size, str(part), part, info))
            else:
                candidates.append((size, str(path), path, {}))
        except (OSError, ValueError) as error:
            if not C.DOCUMENT_SKIP_INVALID:
                raise
            skipped(path, error)
    for size, _, path, split_info in sorted(candidates):
        if size > C.IMPORT_MAX_TOTAL_FILE_MB * 1024 * 1024 - total_bytes:
            skipped(path, 'vượt ngân sách dung lượng của đợt nhập; giữ lại để chia nhỏ hoặc nhập đợt khác')
            continue
        try:
            if split_info:
                with path.open('rb') as handle:
                    if hashlib.file_digest(handle, 'sha256').hexdigest() != split_info['split_file_sha256']:
                        raise ValueError('Phần dữ liệu chia nhỏ bị thay đổi; giữ lại để kiểm tra.')
            extracted = extract_document(path)
        except (OSError, ValueError) as error:
            if not C.DOCUMENT_SKIP_INVALID:
                raise
            skipped(path, error)
            continue
        text = extracted['text']
        if len(text) > C.IMPORT_MAX_TOTAL_CHARACTERS - total_characters:
            skipped(path, 'vượt tổng số ký tự của đợt nhập; giữ nguyên file, không cắt nội dung')
            continue
        for notice in extracted['extraction_warnings']:
            print(f'[Đọc tài liệu] {path.name}: {notice}', file=sys.stderr)
        sha = hashlib.sha256(text.encode()).hexdigest()
        normalized_hash = hashlib.sha256(' '.join(text.split()).encode()).hexdigest()
        if text and normalized_hash not in seen:
            result.append(dict(source=str(path.resolve()), **extracted, **split_info, sha256=sha,
                               normalized_sha256=normalized_hash))
            seen[normalized_hash] = str(path.resolve())
            total_bytes += size
            total_characters += len(text)
        elif text and duplicate_report is not None:
            duplicate_report.add('Toàn file trùng với tài liệu khác trong lần nhập', str(path.resolve()), text,
                                 seen[normalized_hash], whole_file=True)
    return result


def tokenizer_chunks(text):
    size = C.TOKENIZER_CHUNK_CHARACTERS
    if type(size) is not int or size < 256:
        raise ValueError('TOKENIZER_CHUNK_CHARACTERS phải là số nguyên >= 256.')
    for start in range(0, len(text), size):
        yield text[start:start+size]


def shared_chunks(group):
    return {' '.join(part.split()) for doc in group for part in doc['text'].splitlines()
            if len(' '.join(part.split())) >= 80}


def split_documents(docs, seed, duplicate_report=None):
    """Hold validation fixed and remove shared long lines from training only."""
    if not docs:
        raise ValueError('Cần ít nhất 1 tài liệu có nội dung đọc được (TXT/MD, DOCX, PPTX, XLSX/XLS, CSV/TSV, PDF chữ, RTF, HTML).')
    if len(docs) == 1:
        doc = docs[0]
        text = doc['text']
        if len(text) < 2 * C.MIN_TOKENS_PER_SPLIT:
            raise ValueError('Tài liệu quá ngắn để có train/validation độc lập. Bổ sung nội dung; không tạo validation giả.')
        target = max(1, min(len(text) - 1, round(len(text) * .85)))
        # Do not cut a line in half: that would hide duplicate fragments at the boundary.
        # Iterate boundaries instead of allocating one Python integer per word in large files.
        pattern = r'\n' if '\n' in text.strip() else r'\s+'
        boundaries = (m.end() for m in re.finditer(pattern, text) if 0 < m.end() < len(text))
        cut = min(boundaries, key=lambda i: abs(i - target), default=target)
        parts = []
        for start, end in [(0, cut), (cut, len(text))]:
            part = text[start:end]
            parts.append(dict(source=doc['source'], text=part,
                              sha256=hashlib.sha256(part.encode()).hexdigest(),
                              source_sha256=doc.get('source_sha256', doc['sha256']), char_start=start, char_end=end))
        train, valid = [parts[0]], [parts[1]]
    else:
        shuffled = list(docs)
        random.Random(seed).shuffle(shuffled)
        n = max(1, round(len(shuffled) * .15))
        valid, train = shuffled[:n], shuffled[n:]
    overlaps = shared_chunks(train) & shared_chunks(valid)
    cleanup = dict(shared_unique_lines=len(overlaps), removed_train_lines=0, removed_train_characters=0,
                   validation_unchanged=True, files=[])
    if overlaps:
        matched_validation = {}
        if duplicate_report is not None:
            for doc in valid:
                for number, line in enumerate(doc['text'].splitlines(), 1):
                    normalized = ' '.join(line.split())
                    if normalized in overlaps:
                        matched_validation.setdefault(normalized, f'{doc["source"]} — dòng {number} trong phần validation')
        cleaned = []
        for doc in train:
            kept, count, characters = [], 0, 0
            for number, line in enumerate(doc['text'].splitlines(keepends=True), 1):
                if ' '.join(line.split()) in overlaps:
                    if duplicate_report is not None:
                        duplicate_report.add('Trùng validation; bỏ khỏi train', doc['source'], line,
                                             matched_validation[' '.join(line.split())], number)
                    count += 1
                    characters += len(line)
                else:
                    kept.append(line)
            updated = dict(doc)
            if count:
                updated.update(text=''.join(kept), source_sha256=doc.get('source_sha256', doc['sha256']),
                               text_transform='remove_shared_training_lines', removed_overlap_lines=count)
                updated['sha256'] = hashlib.sha256(updated['text'].encode()).hexdigest()
                cleanup['files'].append(dict(source=doc['source'], removed_lines=count, removed_characters=characters))
            cleanup['removed_train_lines'] += count
            cleanup['removed_train_characters'] += characters
            if updated['text'].strip():
                cleaned.append(updated)
        train = cleaned
        print(f'Đã xử lý {len(overlaps):,} đoạn trùng: loại {cleanup["removed_train_lines"]:,} dòng khỏi bản train trong bộ nhớ; '
              'giữ nguyên validation và file nguồn.', flush=True)
    if duplicate_report is not None:
        train = unique_training_lines(train, duplicate_report)
    if not train or not valid:
        raise ValueError('Không đủ dữ liệu độc lập sau khi lọc đoạn trùng. Bổ sung nội dung khác nhau; không tạo validation giả.')
    if shared_chunks(train) & shared_chunks(valid):
        raise ValueError('Vẫn có đoạn trùng giữa train/validation sau xử lý; chưa bắt đầu học.')
    return train, valid, cleanup


def prepare(folder, output, vocab, seed, approved=False, tokenizer=None, history_folder=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = DuplicateReport(output / 'Du_lieu_trung.md')
    status = 'Đang kiểm tra dữ liệu; chưa huấn luyện.'
    try:
        result = _prepare(folder, output, vocab, seed, approved, tokenizer, history_folder, report)
        status = 'Đã chuẩn bị dữ liệu mới sau lọc; báo cáo này không xác nhận phiên huấn luyện đã hoàn tất.'
        return result
    except Exception as error:
        status = f'Chưa chuẩn bị xong dữ liệu: {error}'
        raise
    finally:
        report.write(status)
        print(f'Báo cáo nội dung tạm bỏ qua: {report.path}', flush=True)


class TokenBudgetExceeded(ValueError):
    pass


def encode_training_batch(train, valid, tokenizer, limit):
    """Never retain more than the configured total; discard a failed attempt."""
    encoded, total = {}, 0
    eos = tokenizer.token_to_id('[EOS]')
    for name, group in [('train', train), ('validation', valid)]:
        encoded[name] = []
        for doc in group:
            for part in tokenizer_chunks(doc['text']):
                ids = tokenizer.encode(part).ids
                if total + len(ids) + 1 > limit:
                    raise TokenBudgetExceeded('Vượt ngân sách token của đợt.')
                encoded[name].extend(ids)
                total += len(ids)
            if total + 1 > limit:
                raise TokenBudgetExceeded('Vượt ngân sách token của đợt.')
            encoded[name].append(eos)
            total += 1
    return encoded


def smaller_token_batch(docs, tokenizer, limit):
    """Choose whole sources; never archive a source whose tail was not encoded."""
    counts = []
    for index, doc in enumerate(docs):
        count = 1
        for part in tokenizer_chunks(doc['text']):
            count += len(tokenizer.encode(part).ids)
            if count > limit:
                break
        counts.append((count, index))
    selected, total = set(), 0
    for count, index in sorted(counts):
        if total + count <= limit:
            selected.add(index)
            total += count
    # Re-splitting a single source / removing duplicate lines can change BPE
    # boundaries. Each retry must reduce the source count, even in that case.
    if len(selected) == len(docs):
        selected.remove(max(counts)[1])
    if not selected:
        raise ValueError('Một file/phần riêng lẻ vượt TRAIN_MAX_DATA_TOKENS; chưa thể tạo đợt đủ nhỏ. '
                         'Giảm kích thước phần chia hoặc chia tài liệu này nhỏ hơn. File nguồn được giữ nguyên.')
    return [doc for index, doc in enumerate(docs) if index in selected]


def _prepare(folder, output, vocab, seed, approved, tokenizer, history_folder, report):
    originals = documents(folder, approved, duplicate_report=report, auto_split=True)
    files, lines = historical_index(history_folder, report)
    docs = filter_history(originals, files, lines, report) if history_folder is not None else originals
    if history_folder is not None:
        record_history_skips(originals, docs, report, ROOT)
    if not docs:
        raise ValueError('Không còn nội dung mới để học sau khi bỏ qua dữ liệu trùng, hoặc chưa có tài liệu trong đợt này. '
                         'Xem Du_lieu_trung.md. Nếu nguồn lớn còn dữ liệu, chọn học tài liệu hiện tại lần nữa để lấy phần tiếp theo.')
    if type(C.TRAIN_MAX_DATA_TOKENS) is not int or C.TRAIN_MAX_DATA_TOKENS < 2:
        raise ValueError('TRAIN_MAX_DATA_TOKENS phải là số nguyên >= 2.')
    fixed_tokenizer = tokenizer
    initial_docs = list(docs)
    while True:
        attempt_report = DuplicateReport(report.path)
        try:
            train, valid, cleanup = split_documents(docs, seed, duplicate_report=attempt_report)
        except Exception:
            report.entries.update(attempt_report.entries)
            report.notes.extend(attempt_report.notes)
            raise
        if fixed_tokenizer is None:
            tokenizer = Tokenizer(models.BPE(unk_token='[UNK]'))
            tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
            tokenizer.decoder = decoders.ByteLevel()
            tokenizer.train_from_iterator((part for d in train for part in tokenizer_chunks(d['text'])), trainers.BpeTrainer(
                vocab_size=vocab, special_tokens=['[UNK]', '[EOS]'],
                initial_alphabet=pre_tokenizers.ByteLevel.alphabet(), show_progress=False))
        encoded = None
        try:
            encoded = encode_training_batch(train, valid, tokenizer, C.TRAIN_MAX_DATA_TOKENS)
        except TokenBudgetExceeded:
            # Leave the exception handler before retrying so its traceback cannot
            # retain the discarded token arrays during the next encoding pass.
            pass
        if encoded is not None:
            report.entries.update(attempt_report.entries)
            report.notes.extend(attempt_report.notes)
            break
        docs = smaller_token_batch(docs, tokenizer, C.TRAIN_MAX_DATA_TOKENS)
        print(f'[Chia đợt theo token] Giữ {len(docs)}/{len(initial_docs)} file/phần; '
              f'mã hóa lại trong giới hạn {C.TRAIN_MAX_DATA_TOKENS:,} token. Phần còn lại giữ cho lần học sau.', flush=True)
    selected_sources = {doc['source'] for doc in docs}
    deferred = [doc['source'] for doc in initial_docs if doc['source'] not in selected_sources]
    for source in deferred:
        report.notes.append(f'Chờ đợt sau do ngân sách token (không phải dữ liệu trùng): {source}')
    token_count = sum(map(len, encoded.values()))
    print(f'[Dữ liệu học] {token_count:,}/{C.TRAIN_MAX_DATA_TOKENS:,} token; '
          f'{len(docs)} file/phần được chọn, {len(deferred)} file/phần chờ đợt sau.', flush=True)
    for name, group in [('train', train), ('validation', valid)]:
        if len(encoded[name]) - len(group) < C.MIN_TOKENS_PER_SPLIT:
            suffix = ' sau khi lọc đoạn trùng' if cleanup['removed_train_lines'] else ''
            raise ValueError(f'Tập {name} quá ngắn{suffix}: cần ít nhất {C.MIN_TOKENS_PER_SPLIT} token nội dung để đánh giá có ý nghĩa.')
    manifest = {name: [{k: v for k, v in d.items() if k != 'text'} for d in group]
                for name, group in [('train', train), ('validation', valid)]}
    manifest['seed'] = seed
    manifest['split_strategy'] = 'single_document_text' if len(docs) == 1 else 'document'
    used_sources = {d['source'] for d in train + valid}
    manifest['source_documents'] = [{k: v for k, v in d.items() if k != 'text'} for d in originals if d['source'] in used_sources]
    manifest['duplicate_policy'] = 'NFC + whitespace; skip duplicate files, archived content when requested, shared validation lines and repeated training lines >= 80 characters'
    manifest['overlap_cleanup'] = cleanup
    manifest['duplicate_report'] = report.path.name
    manifest['skipped_duplicate_occurrences'] = sum(e['count'] for e in report.entries.values())
    manifest['tokenizer_chunk_characters'] = C.TOKENIZER_CHUNK_CHARACTERS
    manifest['token_budget'] = dict(limit=C.TRAIN_MAX_DATA_TOKENS, actual=token_count, deferred_sources=deferred)
    manifest['dataset_sha256'] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    tokenizer.save(str(output / 'tokenizer.json'))
    (output / 'tokens.json').write_text(json.dumps(encoded), encoding='utf-8')
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return tokenizer, encoded, manifest


def dataset_changes(folder, manifest, current_documents=None):
    """Read-only comparison; no source files are imported, moved or deleted."""
    current = {d['source']: d['sha256'] for d in (documents(folder) if current_documents is None else current_documents)}
    sources = manifest.get('source_documents')
    if sources is None:
        sources = manifest.get('train', []) + manifest.get('validation', [])
    previous = {d['source']: d.get('source_sha256', d['sha256']) for d in sources}
    return dict(added=sorted(set(current) - set(previous)), removed=sorted(set(previous) - set(current)),
                changed=sorted(p for p in current.keys() & previous.keys() if current[p] != previous[p]))


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
    if type(count) is not int or count < 0 or not isinstance(temperature, (int, float)) or not math.isfinite(temperature) or temperature <= 0:
        raise ValueError('tokens >= 0 và temperature > 0')
    model.eval()
    ids = tokenizer.encode(prompt).ids or [tokenizer.token_to_id('[EOS]')]
    for _ in range(count):
        if interruptible:
            from Model_BimBomAI.Ma_Nguon.runtime import check_stop
            check_stop()
        logits = model(torch.tensor([ids[-model.context:]], device=device))[0, -1].float()
        token = sample_token(logits, temperature)
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


