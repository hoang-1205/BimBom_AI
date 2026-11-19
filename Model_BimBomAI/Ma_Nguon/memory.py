"""Explicitly reviewed memory and SFT examples, independent of model weights."""
import hashlib
import json
import re
import sys
import uuid
from .runtime import ROOT, atomic_json, now


def digest(record):
    value = {k: record[k] for k in ('question', 'answer', 'source')}
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def read_approved(path):
    try:
        entry = json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError, UnicodeError) as error:
        raise ValueError(f'Không đọc được JSON đã duyệt: {path}') from error
    if (not isinstance(entry, dict) or entry.get('status') != 'approved' or entry.get('id') != path.stem
            or any(not isinstance(entry.get(k), str) or not entry[k].strip() for k in ('question', 'answer', 'source'))
            or entry.get('reviewed_sha256') != digest(entry)):
        raise ValueError(f'Ví dụ chưa duyệt hoặc đã bị sửa sau khi duyệt: {path}')
    return entry


class MemoryStore:
    def __init__(self, root=ROOT):
        self.root = root
        self.memory = root / 'Bo_Nho_BimBom/Dai_Han'
        self.pending = root / 'Hoc_BimBom/Cho_Duyet'
        self.sft = root / 'Hoc_BimBom/Du_Lieu_Huan_Luyen/Chat_SFT'
        self.examples = root / 'Ky_Nang_BimBom_Hoc_Duoc/Vi_Du_Chuan'
        self._warned = set()

    @staticmethod
    def read_record(path, pending=False):
        entry = json.loads(path.read_text(encoding='utf-8-sig'))
        fields = ('question', 'answer', 'source') if pending else ('text', 'source', 'kind')
        if (not isinstance(entry, dict) or entry.get('id') != path.stem
                or any(not isinstance(entry.get(k), str) or not entry[k].strip() for k in fields)
                or (pending and entry.get('status') != 'pending')
                or (not pending and (entry.get('confirmed') is not True or entry['kind'] not in ('fact', 'rule', 'workflow')))):
            raise ValueError(f'File bộ nhớ/bản nháp không đúng cấu trúc: {path}')
        return entry

    def records(self, folder, pending=False):
        entries = []
        for path in sorted(folder.glob('*.json')):
            try:
                entry = self.read_record(path, pending)
                self.path(folder, entry['id'])
                entries.append(entry)
            except (OSError, ValueError) as error:
                if str(path) not in self._warned:
                    print(f'Bỏ qua file bộ nhớ/bản nháp lỗi, giữ nguyên để kiểm tra: {path} ({error})', file=sys.stderr)
                    self._warned.add(str(path))
        return entries

    @staticmethod
    def path(folder, identifier):
        if not re.fullmatch(r'[0-9a-f]{32}', identifier):
            raise ValueError('ID không hợp lệ; dùng ID hiển thị trong danh sách.')
        return folder / (identifier + '.json')

    def remember(self, text, source, kind='fact'):
        if not text.strip() or kind not in ('fact', 'rule', 'workflow'):
            raise ValueError('Nội dung hoặc loại ghi nhớ không hợp lệ.')
        entry = dict(id=uuid.uuid4().hex, text=text.strip(), source=source, kind=kind,
                     confirmed=True, created_at=now(), updated_at=now())
        atomic_json(self.path(self.memory, entry['id']), entry)
        self.reindex()
        return entry['id']

    def entries(self):
        return self.records(self.memory)

    def reindex(self):
        entries = self.entries()
        index = [{'id': e['id'], 'terms': sorted(set(re.findall(r'\w+', e['text'].casefold())))} for e in entries]
        atomic_json(self.root / 'Bo_Nho_BimBom/Chi_Muc/memory.json', index)
        for kind, folder in [('rule', 'Quy_Tac_Tra_Loi'), ('workflow', 'Quy_Trinh')]:
            atomic_json(self.root / 'Ky_Nang_BimBom_Hoc_Duoc' / folder / 'entries.json',
                        [e for e in entries if e['kind'] == kind])

    def update(self, identifier, text):
        if not text.strip():
            raise ValueError('Ghi nhớ không được rỗng.')
        path = self.path(self.memory, identifier)
        entry = self.read_record(path)
        entry.update(text=text.strip(), updated_at=now())
        atomic_json(path, entry)
        self.reindex()

    def forget(self, identifier):
        self.path(self.memory, identifier).unlink()
        self.reindex()

    def relevant(self, question, limit=5):
        terms = set(re.findall(r'\w+', question.casefold()))
        ranked = []
        for entry in self.entries():
            score = len(terms & set(re.findall(r'\w+', entry['text'].casefold())))
            if score or entry['kind'] == 'rule':
                ranked.append((score + (entry['kind'] == 'rule'), entry))
        return [e for _, e in sorted(ranked, key=lambda pair: pair[0], reverse=True)[:limit]]

    def correct(self, question, answer, source):
        if not question.strip() or not answer.strip():
            raise ValueError('Cần câu hỏi trước đó và câu trả lời sửa có nội dung.')
        entry = dict(id=uuid.uuid4().hex, question=question.strip(), answer=answer.strip(),
                     source=source, status='pending', created_at=now())
        atomic_json(self.path(self.pending, entry['id']), entry)
        return entry['id']

    def drafts(self):
        return self.records(self.pending, pending=True)

    def approve(self, identifier):
        path = self.path(self.pending, identifier)
        entry = self.read_record(path, pending=True)
        if entry['id'] != identifier or entry['status'] != 'pending':
            raise ValueError('Bản nháp không hợp lệ.')
        entry.update(status='approved', approved_at=now())
        entry['reviewed_sha256'] = digest(entry)
        atomic_json(self.path(self.examples, identifier), entry)
        atomic_json(self.path(self.sft, identifier), entry)
        path.unlink()
        return identifier

    def reject(self, identifier):
        self.path(self.pending, identifier).unlink()
