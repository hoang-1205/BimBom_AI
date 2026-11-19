"""Persistent, bounded queues of CSV records or text chunks. Never moves originals."""
import codecs
import csv
import hashlib
import io
import json
import os
import sys
from pathlib import Path
import uuid
import Chinh_Che_Do as C
from .document_reader import DocumentReadError, detect_csv_delimiter
from .runtime import atomic_json

TEXT_EXTENSIONS = {'', '.txt', '.md', '.markdown', '.text', '.log', '.csv', '.tsv'}


def needs_split(path, size):
    return (C.AUTO_SPLIT_LARGE_FILES and path.suffix.lower() in TEXT_EXTENSIONS
            and size > C.AUTO_SPLIT_TRIGGER_MB * 1024 * 1024)


def version(path):
    stat = path.stat()
    return dict(source=str(path.resolve()), bytes=stat.st_size, modified_ns=stat.st_mtime_ns)


def encoding_for(path):
    if C.DOCUMENT_TEXT_ENCODING != 'auto':
        return C.DOCUMENT_TEXT_ENCODING
    with path.open('rb') as handle:
        prefix = handle.read(4)
    if prefix.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        return 'utf-32'
    if prefix.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return 'utf-16'
    return 'utf-8-sig'


class RecordLines:
    def __init__(self, handle):
        self.handle, self.used = handle, 0

    def __iter__(self):
        return self

    def __next__(self):
        line = self.handle.readline(C.AUTO_SPLIT_MAX_RECORD_CHARACTERS-self.used+1)
        if not line:
            raise StopIteration
        self.used += len(line)
        if self.used > C.AUTO_SPLIT_MAX_RECORD_CHARACTERS:
            raise DocumentReadError('Một bản ghi CSV quá lớn để chia an toàn; tăng AUTO_SPLIT_MAX_RECORD_CHARACTERS hoặc kiểm tra ngoặc kép.')
        return line


def csv_row(row, delimiter):
    buffer = io.StringIO(newline='')
    csv.writer(buffer, delimiter=delimiter, lineterminator='\n').writerow(row)
    return buffer.getvalue()


def pending(state, directory, root):
    from .archive import checked_path, file_hash
    result = []
    for part in state['parts']:
        source = checked_path(directory/part['name'], directory)
        if part.get('skipped_history_report'):
            if not source.is_file() or file_hash(source) != part['sha256']:
                raise ValueError(f'Phần đã bỏ qua do trùng bị thiếu hoặc thay đổi: {source}')
            continue
        if source.exists():
            result.append((source, dict(split_manifest=str(directory/'manifest.json'), split_part=part['name'],
                                       split_file_sha256=part['sha256'], original_source=state['version']['source'])))
        elif part.get('archive_destination'):
            target = checked_path(part['archive_destination'], root/'Da_Hoc')
            if not target.is_file() or file_hash(target) != part['sha256']:
                raise ValueError(f'Phần đã chuyển không còn khớp: {target}. Không tự tạo lại hoặc bỏ qua.')
        else:
            raise ValueError(f'Thiếu phần dữ liệu {source}; chưa có xác nhận chuyển sang Da_Hoc.')
    return result


def split_queue(path, root):
    try:
        return _split_queue(path, root)
    except (csv.Error, UnicodeError) as error:
        raise DocumentReadError(f'{path}: không chia được bản ghi/mã hóa văn bản ({error}); file gốc được giữ nguyên.') from error


def _split_queue(path, root):
    from .archive import checked_path, file_hash
    path, root = Path(path).resolve(), Path(root).resolve()
    for name in ('AUTO_SPLIT_PART_CHARACTERS', 'AUTO_SPLIT_PENDING_PARTS', 'AUTO_SPLIT_MAX_RECORD_CHARACTERS'):
        if type(getattr(C, name)) is not int or getattr(C, name) < 1:
            raise ValueError(f'{name} phải là số nguyên dương.')
    identity = version(path)
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:24]
    directory = checked_path(root/'Hoc_BimBom/Da_Chia'/key, root)
    directory.mkdir(parents=True, exist_ok=True)
    manifest = checked_path(directory/'manifest.json', root)
    is_csv = path.suffix.lower() in ('.csv', '.tsv')
    if manifest.exists():
        state = json.loads(manifest.read_text(encoding='utf-8'))
        if (not isinstance(state, dict) or state.get('format') != 1 or not isinstance(state.get('parts'), list)
                or not all(k in state for k in ('encoding', 'delimiter', 'header', 'offset', 'eof'))
                or any(not isinstance(p, dict) or not all(k in p for k in ('name', 'sha256')) for p in state.get('parts', []))):
            raise ValueError(f'Hàng đợi chia nhỏ không hợp lệ: {manifest}')
        if state.get('version') != identity:
            raise ValueError('Thông tin file gốc không khớp hàng đợi chia nhỏ.')
        ready = pending(state, directory, root)
        if ready or state['eof']:
            return ready
    else:
        encoding = encoding_for(path)
        with path.open(encoding=encoding, newline='') as handle:
            sample = handle.read(32768)
            delimiter, certain = ('\t', True) if path.suffix.lower() == '.tsv' else detect_csv_delimiter(sample)
            if not certain and sample.splitlines():
                delimiter, certain = detect_csv_delimiter(sample.splitlines()[0])
        if is_csv and not certain:
            raise DocumentReadError('Chưa nhận diện được dấu phân cách để tự chia CSV; cần tiêu đề cột rõ ràng.')
        state = dict(version=identity, encoding=encoding, delimiter=delimiter, header=None,
                     offset=0, eof=False, parts=[], format=1)
        if is_csv and C.AUTO_SPLIT_CSV_HAS_HEADER:
            header_limit = csv.field_size_limit()
            try:
                csv.field_size_limit(min(C.AUTO_SPLIT_MAX_RECORD_CHARACTERS, sys.maxsize))
                with path.open(encoding=encoding, newline='') as handle:
                    lines = RecordLines(handle)
                    reader = csv.reader(lines, delimiter=delimiter, strict=True)
                    state['header'] = next(reader, None)
                    state['offset'] = handle.tell()
            finally:
                csv.field_size_limit(header_limit)
        atomic_json(manifest, state)
    old_limit = csv.field_size_limit()
    try:
        csv.field_size_limit(min(C.AUTO_SPLIT_MAX_RECORD_CHARACTERS, sys.maxsize))
        for _ in range(C.AUTO_SPLIT_PENDING_PARTS):
            if state['eof']:
                break
            part_name = f'part_{len(state["parts"])+1:06d}_{uuid.uuid4().hex[:8]}' + ('.csv' if is_csv else '.txt')
            target = checked_path(directory/part_name, root)
            temporary = checked_path(target.with_suffix(target.suffix+'.tmp'), root)
            records, size, eof = 0, 0, False
            next_offset = state['offset']
            try:
                with path.open(encoding=state['encoding'], newline='') as source, temporary.open('x', encoding='utf-8', newline='') as output:
                    source.seek(state['offset'])
                    if is_csv:
                        lines = RecordLines(source)
                        reader = csv.reader(lines, delimiter=state['delimiter'], strict=True)
                        if state['header'] is not None:
                            header = csv_row(state['header'], state['delimiter'])
                            output.write(header)
                            size += len(header)
                    while True:
                        before = source.tell()
                        if is_csv:
                            lines.used = 0
                            row = next(reader, None)
                            text = csv_row(row, state['delimiter']) if row is not None else ''
                        else:
                            text = source.readline(max(1, C.AUTO_SPLIT_PART_CHARACTERS-size))
                        if not text:
                            eof, next_offset = True, source.tell()
                            break
                        if is_csv and records and size+len(text) > C.AUTO_SPLIT_PART_CHARACTERS:
                            next_offset = before
                            break
                        output.write(text)
                        size += len(text)
                        records += 1
                        next_offset = source.tell()
                        if size >= C.AUTO_SPLIT_PART_CHARACTERS:
                            break
                    output.flush()
                    os.fsync(output.fileno())
                if version(path) != identity:
                    raise ValueError('File gốc bị thay đổi trong lúc chia; chưa ghi nhận phần đang xử lý.')
                if records:
                    digest = file_hash(temporary)
                    checked_path(target, root)
                    temporary.rename(target)
                    state['parts'].append(dict(name=part_name, sha256=digest, records=records, characters=size))
                state.update(offset=next_offset, eof=eof)
                atomic_json(manifest, state)
            finally:
                temporary.unlink(missing_ok=True)
    finally:
        csv.field_size_limit(old_limit)
    print(f'[Chia dữ liệu] {path.name}: {len(state["parts"])} phần đã tạo; '
          + ('đã đọc hết nguồn.' if state['eof'] else 'nguồn còn dữ liệu, sẽ đọc tiếp khi các phần chờ đã được dùng.'), flush=True)
    return pending(state, directory, root)


def record_history_skips(originals, filtered, report, root):
    """Advance past wholly archived content, keeping the chunk and its audit on disk."""
    from .archive import checked_path, file_hash
    retained = {doc['source'] for doc in filtered}
    skipped = [doc for doc in originals if doc.get('split_manifest') and doc['source'] not in retained]
    if not skipped:
        return
    report.notes.append(f'{len(skipped)} phần chia hoàn toàn trùng lịch sử: giữ file ở Da_Chia, '
                        'bỏ qua khi lấy đợt tiếp theo; không tính là vừa huấn luyện.')
    report.write('Đã đối chiếu lịch sử; chưa huấn luyện phiên này.')
    for doc in skipped:
        manifest = checked_path(doc['split_manifest'], Path(root)/'Hoc_BimBom/Da_Chia')
        state = json.loads(manifest.read_text(encoding='utf-8'))
        part = next((p for p in state['parts'] if p['name'] == doc['split_part']), None)
        source = checked_path(doc['source'], manifest.parent)
        if (part is None or source != checked_path(manifest.parent/part['name'], manifest.parent)
                or file_hash(source) != part['sha256'] or part['sha256'] != doc['split_file_sha256']):
            raise ValueError('Phần chia đã thay đổi; chưa ghi nhận bỏ qua do trùng lịch sử.')
        part['skipped_history_report'] = str(report.path.resolve())
        atomic_json(manifest, state)


def record_archive_intent(entry, target, root):
    """Persist destination BEFORE rename so a crash after moving cannot lose progress."""
    if not entry.get('split_manifest'):
        return
    from .archive import checked_path
    manifest = checked_path(entry['split_manifest'], Path(root)/'Hoc_BimBom/Da_Chia')
    target = checked_path(target, Path(root)/'Da_Hoc')
    state = json.loads(manifest.read_text(encoding='utf-8'))
    part = next((p for p in state['parts'] if p['name'] == entry['split_part']), None)
    if (part is None or checked_path(manifest.parent/part['name'], manifest.parent) != Path(entry['source']).resolve()
            or part['sha256'] != entry['sha256']):
        raise ValueError('Phần dữ liệu đã thay đổi, không ghi nhận là đã dùng.')
    part['archive_destination'] = str(target)
    atomic_json(manifest, state)
