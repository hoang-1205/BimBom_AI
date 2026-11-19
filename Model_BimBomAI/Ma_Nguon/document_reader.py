"""Read local documents as text without executing Office, macros or formulas."""
import codecs
from collections import Counter
import csv
from datetime import date, datetime
from html.parser import HTMLParser
import io
from itertools import zip_longest
from pathlib import Path
import re
import unicodedata
from zipfile import ZipFile
import Chinh_Che_Do as C

SUPPORTED_EXTENSIONS = frozenset({'.txt', '.md', '.markdown', '.text', '.log', '.csv', '.tsv',
                                  '.docx', '.pptx', '.xlsx', '.xlsm', '.xls', '.pdf', '.rtf', '.html', '.htm'})
CONVERSION_REQUIRED = {'.doc': '.docx', '.ppt': '.pptx', '.xlsb': '.xlsx',
                       '.odt': '.docx', '.odp': '.pptx', '.ods': '.xlsx'}


class DocumentReadError(ValueError):
    pass


def supported_path(path):
    suffix = Path(path).suffix.lower()
    return (suffix in SUPPORTED_EXTENSIONS or suffix in CONVERSION_REQUIRED
            or (not suffix and C.DOCUMENT_READ_EXTENSIONLESS))


class Collector:
    def __init__(self):
        self.parts, self.size = [], 0

    def raw(self, text):
        self.size += len(text)
        if self.size > C.DOCUMENT_MAX_CHARACTERS:
            raise DocumentReadError(f'Nội dung vượt {C.DOCUMENT_MAX_CHARACTERS:,} ký tự. Chia nhỏ tài liệu hoặc chỉnh DOCUMENT_MAX_CHARACTERS.')
        self.parts.append(text)

    def add(self, text):
        text = str(text).strip()
        if text:
            self.raw(text + '\n')

    def text(self):
        return ''.join(self.parts).strip()


def decode_text(data, encoding=None):
    encoding = encoding or C.DOCUMENT_TEXT_ENCODING
    if encoding == 'auto':
        if data.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
            encoding = 'utf-32'
        elif data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
            encoding = 'utf-16'
        else:
            encoding = 'utf-8-sig'
    try:
        text = data.decode(encoding)
    except (UnicodeError, LookupError) as error:
        raise DocumentReadError('Không đọc được mã hóa văn bản. Lưu UTF-8/UTF-16 có BOM, hoặc đặt DOCUMENT_TEXT_ENCODING đúng mã (ví dụ cp1258).') from error
    if '\x00' in text:
        raise DocumentReadError('Nội dung có byte NUL; có thể là file nhị phân hoặc chọn sai mã hóa.')
    return text.replace('\r\n', '\n').replace('\r', '\n')


def _office_archive(path):
    with ZipFile(path) as archive:
        if sum(info.file_size for info in archive.infolist()) > C.DOCUMENT_MAX_ARCHIVE_MB * 1024 * 1024:
            raise DocumentReadError('Tài liệu Office giải nén vượt DOCUMENT_MAX_ARCHIVE_MB; hãy chia nhỏ file.')
        if any(info.flag_bits & 1 for info in archive.infolist()):
            raise DocumentReadError('Không hỗ trợ tài liệu nén có mật khẩu.')


def _value(value):
    if value is None:
        return ''
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    return str(value).replace('\r\n', '\n').replace('\r', '\n')


def _row(collector, cells):
    values = [_value(cell) for cell in cells]
    while values and not values[-1]:
        values.pop()
    if any(values):
        collector.raw('\t'.join(values) + '\n')


def _docx(path, out, notices):
    from docx import Document
    from docx.table import Table
    def blocks(parent):
        for block in parent.iter_inner_content():
            if isinstance(block, Table):
                for row in block.rows:
                    cells, previous = [], None
                    for cell in row.cells:
                        # Merged cells appear more than once; do not duplicate their text.
                        if cell._tc is previous:
                            cells.append('')
                        else:
                            cells.append('\n'.join(blocks(cell)))
                        previous = cell._tc
                    yield '\t'.join(cells)
            else:
                yield block.text
    document = Document(path)
    for text in blocks(document):
        out.add(text)
    notices.append('Word: đọc đoạn văn và bảng trong thân tài liệu; không OCR ảnh, không lấy textbox/header/footer/chú thích.')


def _pptx(path, out, notices):
    from pptx import Presentation
    def shape_text(shape):
        if hasattr(shape, 'shapes'):
            for child in shape.shapes:
                shape_text(child)
        if getattr(shape, 'has_text_frame', False):
            out.add(shape.text_frame.text.replace('\v', '\n'))
        if getattr(shape, 'has_table', False):
            for row in shape.table.rows:
                _row(out, [cell.text if not cell.is_spanned else '' for cell in row.cells])
    presentation = Presentation(path)
    for index, slide in enumerate(presentation.slides, 1):
        start = out.size
        for shape in slide.shapes:
            shape_text(shape)
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                out.add('Ghi chú người trình bày: ' + notes)
        if out.size == start:
            notices.append(f'Slide {index}: không có chữ trích xuất được (ảnh/biểu đồ cần chuyển thành văn bản).')
    notices.append('PowerPoint: thứ tự chữ theo slide/shape; không diễn giải hình ảnh, biểu đồ hoặc tệp nhúng.')


def _xlsx(path, out, notices):
    from openpyxl import load_workbook
    formulas = load_workbook(path, read_only=True, data_only=False, keep_links=False)
    cached = None
    try:
        cached = load_workbook(path, read_only=True, data_only=True, keep_links=False)
        cells_read, missing = 0, 0
        for sheet in formulas.worksheets:
            heading_written = False
            values_sheet = cached[sheet.title]
            sheet.reset_dimensions()
            values_sheet.reset_dimensions()
            for row, value_row in zip_longest(sheet.iter_rows(), values_sheet.iter_rows(), fillvalue=()):
                cells_read += max(len(row), len(value_row))
                if cells_read > C.DOCUMENT_MAX_CELLS:
                    raise DocumentReadError('Bảng tính vượt DOCUMENT_MAX_CELLS; hãy tách file hoặc thu gọn vùng dữ liệu.')
                result = []
                for cell, value_cell in zip_longest(row, value_row):
                    value = value_cell.value if value_cell is not None else None
                    if cell is not None and cell.data_type == 'f' and value is None:
                        missing += 1
                        value = f'[Công thức chưa có kết quả lưu: {cell.value}]'
                    result.append(value)
                if any(value is not None and str(value).strip() for value in result):
                    if not heading_written:
                        out.add('Trang tính: ' + sheet.title + (' (ẩn)' if sheet.sheet_state != 'visible' else ''))
                        heading_written = True
                    _row(out, result)
        if missing:
            notices.append(f'{missing} ô công thức chưa có kết quả lưu; giữ công thức có nhãn, không tự tính kết quả.')
        notices.append('Excel: đọc tất cả trang tính, kể cả trang ẩn. Giá trị công thức là kết quả lưu lần trước; không chạy macro/liên kết ngoài.')
    finally:
        formulas.close()
        if cached is not None:
            cached.close()


def _xls(path, out, notices):
    import xlrd
    book = xlrd.open_workbook(str(path), on_demand=True, logfile=io.StringIO())
    try:
        cells_read = 0
        for sheet in book.sheets():
            heading_written = False
            cells_read += sheet.nrows * sheet.ncols
            if cells_read > C.DOCUMENT_MAX_CELLS:
                raise DocumentReadError('Bảng tính XLS vượt DOCUMENT_MAX_CELLS.')
            for row in sheet.get_rows():
                values = []
                for cell in row:
                    value = cell.value
                    if cell.ctype == xlrd.XL_CELL_DATE:
                        value = xlrd.xldate.xldate_as_datetime(value, book.datemode)
                    elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                        value = bool(value)
                    elif cell.ctype == xlrd.XL_CELL_ERROR:
                        value = xlrd.error_text_from_code.get(value, '#ERROR')
                    values.append(value)
                if any(value is not None and str(value).strip() for value in values):
                    if not heading_written:
                        out.add('Trang tính: ' + sheet.name)
                        heading_written = True
                    _row(out, values)
        notices.append('XLS: chỉ đọc giá trị đã lưu; không tính lại công thức hoặc chạy macro.')
    finally:
        book.release_resources()


def detect_csv_delimiter(content):
    """Inspect complete records; do not infer a dialect from truncated quoted text."""
    candidates = []
    for delimiter in (',', ';', '\t', '|'):
        widths, header = [], None
        try:
            reader = csv.reader(io.StringIO(content, newline=''), delimiter=delimiter, strict=True)
            for row in reader:
                if not row:
                    continue
                if header is None:
                    header = row
                widths.append(len(row))
                if len(widths) >= 61:
                    break
        except csv.Error:
            continue
        if not widths or len(header) < 2:
            continue
        width, matches = Counter(widths).most_common(1)[0]
        plain_header = all(re.fullmatch(r'[^\W\d][\w -]*', cell.strip()) for cell in header)
        candidates.append(dict(delimiter=delimiter, consistent=width == len(header) and matches/len(widths) >= .95,
                               header=plain_header))
    strong = [c for c in candidates if c['consistent']]
    if len(strong) == 1:
        return strong[0]['delimiter'], True
    headers = [c for c in (strong or candidates) if c['header']]
    if len(headers) == 1:
        return headers[0]['delimiter'], True
    return ',', False


def _csv(path, out, notices):
    if type(C.DOCUMENT_MAX_CHARACTERS) is not int or C.DOCUMENT_MAX_CHARACTERS < 1:
        raise DocumentReadError('DOCUMENT_MAX_CHARACTERS phải là số nguyên dương.')
    content = decode_text(path.read_bytes())
    count = 0
    # newline='' preserves quoted cells containing line breaks.
    previous_limit = csv.field_size_limit()
    try:
        # A CSV field cannot contain more characters than the complete input.
        # Bound the native ssize_t argument even if the Python config integer is enormous.
        csv.field_size_limit(min(C.DOCUMENT_MAX_CHARACTERS, max(1, len(content))))
        delimiter, certain = ('\t', True) if path.suffix.lower() == '.tsv' else detect_csv_delimiter(content)
        if not certain:
            notices.append('Không nhận diện chắc chắn dấu phân cách CSV; dùng dấu phẩy.')
        dictionary_schemas = {
            ('english', 'vietnamese_analytics'),
            ('diacritical_marks_vietnamese', 'no_accents_mark_vietnamese', 'mean'),
        }
        expected, dictionary, merged, irregular = None, False, 0, 0
        for row in csv.reader(io.StringIO(content, newline=''), delimiter=delimiter, strict=True):
            if not row:
                continue
            if expected is None:
                expected = len(row)
                dictionary = delimiter == ',' and tuple(cell.strip().casefold() for cell in row) in dictionary_schemas
            elif len(row) != expected:
                if dictionary and len(row) > expected:
                    # These dictionary exports put free-form meanings in the final column.
                    # Repair only their explicit schemas, not arbitrary ragged CSV tables.
                    row = row[:expected-1] + [delimiter.join(row[expected-1:])]
                    merged += 1
                else:
                    irregular += 1
            count += len(row)
            if count > C.DOCUMENT_MAX_CELLS:
                raise DocumentReadError('CSV/TSV vượt DOCUMENT_MAX_CELLS.')
            _row(out, row)
        if merged:
            notices.append(f'CSV từ điển: nhận diện dấu phẩy từ tiêu đề; giữ dấu phẩy trong cột nghĩa của {merged:,} bản ghi. Không sửa file gốc.')
        if irregular:
            notices.append(f'CSV: {irregular:,} bản ghi có số cột khác dòng đầu; giữ nguyên các ô đã đọc, không tự gộp cột.')
    finally:
        csv.field_size_limit(previous_limit)


def _pdf(path, out, notices):
    from pypdf import PdfReader
    with path.open('rb') as stream:
        reader = PdfReader(stream)
        if reader.is_encrypted and not reader.decrypt(''):
            raise DocumentReadError('PDF có mật khẩu; cung cấp bản đã mở khóa.')
        empty = []
        for index, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ''
            if text.strip():
                out.add(text)
            else:
                empty.append(index)
        if empty:
            notices.append(f'{len(empty)} trang PDF không có chữ trích xuất được; có thể cần OCR. Trang đầu: {empty[:10]}')
        if not out.text():
            raise DocumentReadError('PDF không có lớp chữ đọc được. Cần OCR/chuyển thành văn bản trước.')


def _rtf(path, out, notices):
    from striprtf.striprtf import rtf_to_text
    data = path.read_bytes()
    codepage = re.search(rb'\\ansicpg(\d+)', data[:4096])
    encoding = 'cp' + codepage.group(1).decode('ascii') if codepage else 'cp1252'
    text = decode_text(data, encoding)
    out.add(rtf_to_text(text, encoding=encoding, errors='strict'))


class TextHTMLParser(HTMLParser):
    blocked = {'script', 'style', 'head', 'template', 'noscript'}
    blocks = {'p', 'div', 'br', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'section', 'article'}

    def __init__(self, collector):
        super().__init__(convert_charrefs=True)
        self.collector, self.hidden = collector, []

    def handle_starttag(self, tag, attrs):
        if tag in self.blocked:
            self.hidden.append(tag)
        if not self.hidden:
            if tag in self.blocks:
                self.collector.raw('\n')
            elif tag in {'td', 'th'}:
                self.collector.raw('\t')

    def handle_endtag(self, tag):
        if self.hidden:
            if tag == self.hidden[-1]:
                self.hidden.pop()
        elif tag in self.blocks:
            self.collector.raw('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.collector.raw(data)


def _html(path, out, notices):
    parser = TextHTMLParser(out)
    parser.feed(decode_text(path.read_bytes()))
    parser.close()
    notices.append('HTML: chỉ lấy chữ trong file cục bộ; không chạy JavaScript, tải ảnh hoặc truy cập liên kết.')


READERS = {'.docx': _docx, '.pptx': _pptx, '.xlsx': _xlsx, '.xlsm': _xlsx, '.xls': _xls,
           '.csv': _csv, '.tsv': _csv, '.pdf': _pdf, '.rtf': _rtf, '.html': _html, '.htm': _html}


def extract_document(path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in CONVERSION_REQUIRED:
        raise DocumentReadError(f'{path}: định dạng {suffix} cần chuyển sang {CONVERSION_REQUIRED[suffix]} trước khi đọc.')
    if not supported_path(path):
        raise DocumentReadError(f'{path}: định dạng chưa hỗ trợ. Các đuôi hỗ trợ: {", ".join(sorted(SUPPORTED_EXTENSIONS))}')
    try:
        if path.stat().st_size > C.DOCUMENT_MAX_FILE_MB * 1024 * 1024:
            raise DocumentReadError('File vượt DOCUMENT_MAX_FILE_MB; chia nhỏ trước khi đọc.')
        if suffix in {'.docx', '.pptx', '.xlsx', '.xlsm'}:
            _office_archive(path)
        out, notices = Collector(), []
        if suffix in READERS:
            READERS[suffix](path, out, notices)
        else:
            out.raw(decode_text(path.read_bytes()))
        text = unicodedata.normalize('NFC', out.text()).strip()
        if not text:
            notices.append('File không có nội dung văn bản; không được đưa vào tập học.')
        return dict(text=text, format=suffix[1:] or 'text', extraction_warnings=notices, reader_version=1)
    except ImportError as error:
        raise DocumentReadError(f'{path}: thiếu thư viện đọc tài liệu. Chạy Model_BimBomAI/setup.ps1 hoặc cài requirements-documents.txt bằng Python của dự án.') from error
    except DocumentReadError as error:
        raise DocumentReadError(f'{path}: {error}') from error
    except Exception as error:
        raise DocumentReadError(f'{path}: không đọc được tài liệu ({type(error).__name__}: {error}). Kiểm tra định dạng, mật khẩu hoặc file bị hỏng.') from error
