"""Exact duplicate filtering with a human-readable audit; never edits sources."""
import hashlib
import os
from pathlib import Path
import re
import tempfile
import unicodedata
from .document_reader import extract_document, supported_path
import Chinh_Che_Do as C


def normalized(text):
    return ' '.join(unicodedata.normalize('NFC', text).split())


def key(text):
    return hashlib.sha256(normalized(text).encode()).hexdigest()


class DuplicateReport:
    def __init__(self, path):
        self.path = Path(path)
        self.entries = {}
        self.notes = []

    def add(self, reason, source, content, matched, line=None, whole_file=False):
        digest = key(content)
        identity = (reason, str(source), digest, str(matched), whole_file)
        if identity not in self.entries:
            self.entries[identity] = dict(reason=reason, source=str(source), matched=str(matched),
                                          digest=digest, content='' if whole_file else content.rstrip(),
                                          whole_file=whole_file, lines=[], count=0)
        entry = self.entries[identity]
        entry['count'] += 1
        if line is not None:
            entry['lines'].append(line)

    def write(self, status):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=self.path.parent, suffix='.tmp', delete=False) as handle:
                temporary = Path(handle.name)
                handle.write('# Báo cáo dữ liệu trùng đã tạm bỏ qua\n\n')
                handle.write(f'Trạng thái: {status}\n\n')
                handle.write(f'Số nhóm nội dung trùng: {len(self.entries)}. Tổng lượt bỏ qua: {sum(e["count"] for e in self.entries.values())}.\n\n')
                handle.write('File gốc không bị sửa hoặc xóa. Dòng bên dưới là dòng của văn bản trích xuất/phần dữ liệu đang xét, không phải số hàng Excel hay bản ghi CSV. '
                             'So khớp toàn file và dòng có ít nhất 80 ký tự sau chuẩn hóa Unicode/khoảng trắng; không nhận diện trùng nghĩa. '
                             'Nội dung trong Da_Hoc là dữ liệu đã dùng trước đây, không chứng minh mô hình đã nắm vững nội dung.\n\n')
                for note in self.notes:
                    handle.write(f'- {note}\n')
                if not self.entries:
                    handle.write('\nKhông phát hiện nội dung trùng theo tiêu chí trên.\n')
                for index, entry in enumerate(self.entries.values(), 1):
                    handle.write(f'\n## {index}. {entry["reason"]}\n\n')
                    for label, value in [('Nguồn bị bỏ qua', entry['source']), ('Trùng với', entry['matched'])]:
                        handle.write(f'{label}:\n\n    {value.replace(chr(10), " ")}\n\n')
                    handle.write(f'Số lần: {entry["count"]}. SHA-256 nội dung chuẩn hóa: `{entry["digest"]}`.\n\n')
                    if entry['lines']:
                        handle.write('Dòng: ' + ', '.join(map(str, entry['lines'])) + '.\n\n')
                    if entry['whole_file']:
                        handle.write('Toàn bộ nội dung file bị trùng; xem file gốc ở đường dẫn trên.\n')
                    else:
                        longest = max((len(m.group()) for m in re.finditer(r'`+', entry['content'])), default=0)
                        fence = '`' * max(3, longest+1)
                        handle.write(f'{fence}text\n{entry["content"]}\n{fence}\n')
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def historical_index(folder, report):
    """Index only supported local documents under the explicitly supplied archive."""
    files, lines = {}, {}
    if folder is None or not Path(folder).exists():
        return files, lines
    folder = Path(folder).absolute()
    if folder.is_symlink() or folder.is_junction():
        raise ValueError('Da_Hoc là liên kết; không đọc lịch sử qua liên kết.')
    for path in sorted(folder.rglob('*')):
        if not path.is_file() or path.name.startswith('~$') or not supported_path(path):
            continue
        if not path.resolve().is_relative_to(folder.resolve()) or path.is_symlink() or path.is_junction():
            continue
        # Check intermediate directories as well as the file itself.
        if any(p.is_symlink() or p.is_junction() for p in path.parents if p.is_relative_to(folder)):
            continue
        try:
            text = extract_document(path)['text']
        except (ValueError, OSError) as error:
            if not C.DOCUMENT_SKIP_INVALID:
                raise
            report.notes.append(f'Không đối chiếu được lịch sử {path}: {error}. Không xác định được trùng với file này.')
            continue
        if text.strip():
            files.setdefault(key(text), str(path))
        for number, line in enumerate(text.splitlines(), 1):
            if len(normalized(line)) >= 80:
                lines.setdefault(key(line), f'{path} — dòng {number}')
    report.notes.append(f'Đã đối chiếu lịch sử trong {folder}; {len(files)} nội dung file khác nhau.')
    return files, lines


def filter_history(docs, files, lines, report):
    result = []
    for doc in docs:
        match = files.get(key(doc['text']))
        if match:
            report.add('Toàn file đã có trong Da_Hoc', doc['source'], doc['text'], match, whole_file=True)
            continue
        kept, count = [], 0
        for number, line in enumerate(doc['text'].splitlines(keepends=True), 1):
            match = lines.get(key(line)) if len(normalized(line)) >= 80 else None
            if match:
                report.add('Nội dung đã có trong Da_Hoc', doc['source'], line, match, number)
                count += 1
            else:
                kept.append(line)
        updated = transformed(doc, ''.join(kept), 'skip_archived_lines') if count else dict(doc)
        if updated['text'].strip():
            result.append(updated)
    return result


def transformed(doc, text, operation):
    return dict(doc, text=text, source_sha256=doc.get('source_sha256', doc['sha256']),
                sha256=hashlib.sha256(text.encode()).hexdigest(), text_transform=operation)


def unique_training_lines(group, report):
    seen, result = {}, []
    for doc in group:
        kept = []
        for number, line in enumerate(doc['text'].splitlines(keepends=True), 1):
            digest = key(line) if len(normalized(line)) >= 80 else None
            if digest and digest in seen:
                report.add('Lặp trong tập train; giữ lần xuất hiện đầu', doc['source'], line, seen[digest], number)
            else:
                kept.append(line)
                if digest:
                    seen[digest] = f'{doc["source"]} — dòng {number} trong phần train'
        text = ''.join(kept)
        if text.strip():
            result.append(transformed(doc, text, 'skip_duplicate_training_lines') if text != doc['text'] else dict(doc))
    return result
