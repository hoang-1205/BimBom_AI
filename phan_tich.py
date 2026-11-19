"""Đối chiếu hồ sơ với tiêu chí nghề nghiệp minh bạch; không dùng trọng số AI."""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import unicodedata
from Model_BimBomAI.bao_cao import save_review, analysis_text

ROOT = Path(__file__).resolve().parent


def normalize(value):
    return ' '.join(unicodedata.normalize('NFC', value).casefold().split())


def number(value, label, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label}: cần số hữu hạn.')
    if value < 0 or (maximum is not None and value > maximum):
        raise ValueError(f'{label}: giá trị ngoài phạm vi.')
    return value


def strings(value, label):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValueError(f'{label}: cần danh sách chuỗi không rỗng.')
    return {normalize(v) for v in value}


def analyze(profile, catalog):
    if not isinstance(profile, dict) or not isinstance(catalog, dict):
        raise ValueError('Hồ sơ và tiêu chí phải là đối tượng JSON.')
    skills = profile.get('ky_nang', {})
    if not isinstance(skills, dict):
        raise ValueError('ky_nang phải là đối tượng tên kỹ năng: mức 0–5.')
    normalized = {}
    for key, value in skills.items():
        if not isinstance(key, str) or not key.strip() or normalize(key) in normalized:
            raise ValueError('Tên kỹ năng rỗng hoặc trùng sau chuẩn hóa.')
        normalized[normalize(key)] = number(value, key, 5)
    fields = strings(profile.get('nganh_hoc', []), 'nganh_hoc')
    experience = profile.get('kinh_nghiem_lien_quan', {})
    if not isinstance(experience, dict):
        raise ValueError('kinh_nghiem_lien_quan phải là đối tượng mã nghề: số năm.')
    for key, value in experience.items():
        number(value, f'Kinh nghiệm {key}')
    roles = catalog.get('nghe')
    if not isinstance(roles, list) or not roles:
        raise ValueError('Danh sách nghe trong tiêu chí không được rỗng.')
    results, seen = [], set()
    for role in roles:
        identifier, name = role['id'], role['ten']
        if not isinstance(identifier, str) or not identifier.strip() or identifier in seen:
            raise ValueError('Mã nghề rỗng hoặc trùng.')
        if not isinstance(name, str) or not name.strip():
            raise ValueError('Tên nghề không hợp lệ.')
        seen.add(identifier)
        required = role['ky_nang']
        if not isinstance(required, dict) or not required:
            raise ValueError(f'{identifier}: cần tiêu chí kỹ năng.')
        recognized, missing, gaps = [], [], []
        total = 0
        keys = set()
        for skill, target in required.items():
            if not isinstance(skill, str) or not skill.strip() or normalize(skill) in keys:
                raise ValueError('Kỹ năng tiêu chí trùng hoặc rỗng.')
            keys.add(normalize(skill))
            if number(target, skill, 5) == 0:
                raise ValueError('Mức kỹ năng yêu cầu phải lớn hơn 0.')
            level = normalized.get(normalize(skill))
            if level is None:
                missing.append(skill)
                continue
            total += min(level / target, 1)
            item = dict(ky_nang=skill, muc_khai_bao=level, muc_muc_tieu=target)
            (recognized if level >= target else gaps).append(item)
        related = strings(role['nganh_hoc'], 'Ngành học trong tiêu chí')
        if not related:
            raise ValueError('Cần ngành học liên quan trong tiêu chí.')
        years = number(role['so_nam_muc_tieu'], 'Số năm mục tiêu')
        if years == 0:
            raise ValueError('Số năm mục tiêu phải lớn hơn 0.')
        actual_years = experience.get(identifier)
        skill_points = 70 * total / len(required)
        field_points = 15 if fields & related else 0
        exp_points = 15 * min(actual_years / years, 1) if actual_years is not None else 0
        coverage = (70 * (len(required)-len(missing))/len(required)
                    + (15 if fields else 0) + (15 if actual_years is not None else 0))
        results.append(dict(id=identifier, ten=name,
            diem_doi_chieu=round(skill_points + field_points + exp_points, 2),
            do_day_du_du_lieu=round(coverage, 2),
            diem_thanh_phan=dict(ky_nang=round(skill_points, 2), nganh_hoc=field_points,
                                kinh_nghiem=round(exp_points, 2)),
            ky_nang_dat=recognized, ky_nang_can_bo_sung=gaps, ky_nang_chua_khai_bao=missing,
            nganh_hoc_trung=sorted(fields & related),
            kinh_nghiem=dict(da_khai_bao=actual_years, muc_tieu=years),
            can_bo_sung_thong_tin=(['nganh_hoc'] if not fields else []) +
                                   (['kinh_nghiem_lien_quan.' + identifier] if actual_years is None else [])))
    results.sort(key=lambda r: (-r['diem_doi_chieu'], -r['do_day_du_du_lieu'], r['id']))
    return dict(phuong_phap='doi_chieu_tieu_chi_v1',
        luu_y='Điểm đối chiếu không phải xác suất thành công hay kết luận năng lực. Thông tin chưa khai báo không chứng minh thiếu năng lực. Tiêu chí mẫu cần được kiểm tra cho mục đích thực tế.',
        trang_thai='Có dữ liệu để đối chiếu' if any(r['do_day_du_du_lieu'] for r in results) else 'Chưa đủ dữ liệu; chưa nên xếp hạng phù hợp',
        ket_qua=results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ho_so', type=Path, nargs='?', default=ROOT / 'Du_Lieu/Phan_Tich' / 'ho_so_mau.json')
    parser.add_argument('--tieu-chi', type=Path, default=ROOT / 'Du_Lieu/Phan_Tich' / 'tieu_chi_nghe.json')
    args = parser.parse_args()
    try:
        profile = json.loads(args.ho_so.read_text(encoding='utf-8-sig'))
        catalog_text = args.tieu_chi.read_text(encoding='utf-8-sig')
        result = analyze(profile, json.loads(catalog_text))
        result['nguon_ho_so'] = str(args.ho_so.resolve())
        result['nguon_tieu_chi'] = str(args.tieu_chi.resolve())
        result['ma_tieu_chi'] = hashlib.sha256(catalog_text.encode()).hexdigest()
        result['thoi_diem'] = datetime.now().astimezone().isoformat()
        folder = ROOT / 'Ket_Qua/Ket_qua_BimBom'
        folder.mkdir(parents=True, exist_ok=True)
        output = folder / ('phan_tich_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')
        with output.open('x', encoding='utf-8') as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
        print(result['trang_thai'])
        for item in result['ket_qua']:
            print(f"{item['ten']}: {item['diem_doi_chieu']}/100; dữ liệu {item['do_day_du_du_lieu']}%")
            print('  Chưa khai báo kỹ năng:', ', '.join(item['ky_nang_chua_khai_bao']) or 'không')
        print(result['luu_y'])
        print('Chi tiết:', output)
        review = save_review(json.dumps(profile, ensure_ascii=False, indent=2), analysis_text(result),
                             f"Hồ sơ: {result['nguon_ho_so']}\nTiêu chí: {result['nguon_tieu_chi']}\nMã tiêu chí: {result['ma_tieu_chi']}\nBáo cáo JSON: {output.resolve()}",
                             kind='phan_tich')
        print('Bản Markdown cho giáo viên:', review)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'Lỗi: {error}\n')


if __name__ == '__main__':
    main()


