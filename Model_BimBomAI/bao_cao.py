"""Lưu nội dung cần giáo viên kiểm tra, độc lập với kho đã duyệt."""
from datetime import datetime
from pathlib import Path
import re
import uuid

ROOT = Path(__file__).resolve().parent.parent


def block(text):
    text = str(text)
    size = max([len(m.group()) for m in re.finditer(r'`+', text)] + [2]) + 1
    fence = '`' * size
    return f'{fence}text\n{text}\n{fence}'


def save_review(user_text, answer, source, kind='tra_loi', folder=None):
    folder = Path(folder) if folder is not None else ROOT / 'Ket_Qua'
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone()
    prefix = 'phan_tich' if kind == 'phan_tich' else 'tra_loi'
    path = folder / f'{prefix}_{now:%Y%m%d_%H%M%S_%f}_{uuid.uuid4().hex[:8]}.md'
    content = (f'# BimBom — Phiếu kiểm tra {"phân tích" if prefix == "phan_tich" else "câu trả lời"}\n\n'
               f'- Thời gian: {now.isoformat(timespec="seconds")}\n'
               '- Trạng thái: **Chờ giáo viên kiểm tra**\n\n'
               f'## Nội dung người dùng cung cấp\n\n{block(user_text)}\n\n'
               f'## Kết quả của BimBom\n\n{block(answer)}\n\n'
               f'## Nguồn và chế độ xử lý\n\n{block(source)}\n\n'
               '## Nhận xét của giáo viên\n\n'
               '- Người kiểm tra: \n- Ngày kiểm tra: \n'
               '- Kết luận: Chưa kiểm tra / Đạt / Cần sửa\n'
               '- Nội dung đúng và căn cứ: \n- Nội dung sai hoặc còn thiếu: \n'
               '- Câu trả lời hoặc cách làm đã sửa: \n\n'
               'Ghi nhận xét trong file này không tự duyệt kỹ năng và không tự huấn luyện AI.\n')
    with path.open('x', encoding='utf-8') as handle:
        handle.write(content)
    return path


def analysis_text(result):
    lines = [result['trang_thai'], result['luu_y']]
    for i, role in enumerate(result['ket_qua'], 1):
        lines += ['', f"{i}. {role['ten']} ({role['id']})",
                  f"Điểm đối chiếu: {role['diem_doi_chieu']}/100; dữ liệu đã cung cấp: {role['do_day_du_du_lieu']}%",
                  'Điểm thành phần: ' + ', '.join(f'{k}: {v}' for k, v in role['diem_thanh_phan'].items())]
        for key, label in [('ky_nang_dat', 'Kỹ năng đạt mức mục tiêu'), ('ky_nang_can_bo_sung', 'Kỹ năng cần bổ sung')]:
            lines.append(label + ': ' + ('; '.join(f"{s['ky_nang']} ({s['muc_khai_bao']}/{s['muc_muc_tieu']})" for s in role[key]) or 'Không có'))
        lines += ['Kỹ năng chưa khai báo: ' + (', '.join(role['ky_nang_chua_khai_bao']) or 'Không có'),
                  'Ngành học trùng: ' + (', '.join(role['nganh_hoc_trung']) or 'Chưa ghi nhận'),
                  f"Kinh nghiệm liên quan: {role['kinh_nghiem']['da_khai_bao'] if role['kinh_nghiem']['da_khai_bao'] is not None else 'Chưa khai báo'}; mục tiêu: {role['kinh_nghiem']['muc_tieu']} năm",
                  'Thông tin cần hỏi thêm: ' + (', '.join(role['can_bo_sung_thong_tin']) or 'Không có')]
    return '\n'.join(lines)
