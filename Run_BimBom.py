"""Bộ điều khiển chat/train/status cho một môi trường Python."""
import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path
import torch
import Chinh_Che_Do as C
from Model_BimBomAI.pipeline import documents
from Model_BimBomAI.Ma_Nguon.checkpoint import discover, validate
from Model_BimBomAI.Ma_Nguon.memory import read_approved
from Model_BimBomAI.Ma_Nguon.runtime import ROOT, initialize, request_stop, wait_stopped, active_session, read_input, session_lock


def expected_architecture():
    return dict(context=C.CONTEXT_LENGTH, dim=C.MODEL_DIM, heads=C.MODEL_HEADS, layers=C.MODEL_LAYERS)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    chat = sub.add_parser('chat', help='Trò chuyện và dạy bằng bộ nhớ xác nhận')
    train = sub.add_parser('train', help='Huấn luyện thêm N bước')
    status = sub.add_parser('status', help='Kiểm tra môi trường và checkpoint')
    stop = sub.add_parser('stop', aliases=['tat'], help='Tắt chat hoặc lưu checkpoint và dừng train')
    stop.add_argument('--wait', type=int, default=30, help='Số giây chờ phiên kết thúc (mặc định 30)')
    for parser in (chat, train, status, stop):
        parser.add_argument('name', choices=['bimbom'])
    for parser in (chat, train):
        parser.add_argument('--device', choices=['auto', 'cpu', 'cuda'])
    chat.add_argument('--mode', choices=['CHAT_ONLY', 'CHAT_MEMORY', 'CHAT_COLLECT_TRAIN'])
    chat.add_argument('--checkpoint', type=Path)
    train.add_argument('--steps', type=int, help='Số bước muốn huấn luyện THÊM')
    select = train.add_mutually_exclusive_group()
    select.add_argument('--new', action='store_true', help='Khởi tạo mô hình mới từ đầu')
    select.add_argument('--checkpoint', type=Path, help='Resume checkpoint chỉ định')
    select.add_argument('--init-from', type=Path, help='Giữ trọng số, đổi tập dữ liệu và tạo optimizer mới')
    train.add_argument('--stage', choices=['pretrain', 'sft'])
    train.add_argument('--folder', type=Path)
    status.add_argument('--json', action='store_true')
    args = p.parse_args()
    initialize()
    if Path(sys.prefix).resolve() != (ROOT / 'Model_BimBomAI/.venv').resolve():
        p.error('Dùng run.cmd để chạy đúng môi trường Model_BimBomAI/.venv.')
    if args.command in ('stop', 'tat'):
        if args.wait < 0:
            p.error('--wait phải >= 0')
        session = request_stop(ROOT)
        if session is None:
            print('BimBom hiện không chạy.')
            return 0
        print(f"Đã gửi yêu cầu tắt phiên {session['kind']}. Nếu đang train, chờ hoàn tất bước và lưu checkpoint.", flush=True)
        if wait_stopped(session['id'], args.wait, ROOT):
            print('Phiên BimBom đã kết thúc.')
            return 0
        print('Yêu cầu tắt vẫn có hiệu lực; phiên chưa kết thúc trong thời gian chờ. Dùng run status bimbom để kiểm tra.')
        return 2
    if args.command == 'status':
        checkpoint, saved, skipped = discover(expected=expected_architecture())
        result = dict(python=platform.python_version(), executable=sys.executable,
                      torch=str(torch.__version__), cuda_available=torch.cuda.is_available(),
                      gpu=torch.cuda.get_device_name() if torch.cuda.is_available() else None,
                      configured_device=C.CHE_DO, chat_mode=C.CHAT_MODE,
                      active_session=active_session(ROOT),
                      checkpoint=str(checkpoint) if checkpoint else None,
                      step=saved['step'] if saved else 0, stage=saved.get('stage', 'pretrain') if saved else None,
                      pretrain_documents=len(documents(ROOT / 'Hoc_BimBom')),
                      pending=len(list((ROOT / 'Hoc_BimBom/Cho_Duyet').glob('*.json'))),
                      approved_sft=len(list((ROOT / 'Hoc_BimBom/Du_Lieu_Huan_Luyen/Chat_SFT').glob('*.json'))),
                      memories=len(list((ROOT / 'Bo_Nho_BimBom/Dai_Han').glob('*.json'))),
                      skipped_checkpoints=skipped)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not args.json and not checkpoint:
            print('Chưa có checkpoint tương thích. Thêm dữ liệu Pretrain để huấn luyện từ đầu; chat vẫn lưu được bộ nhớ.')
        return 0
    command = [sys.executable, '-B', str(ROOT / ('Chat_BimBom.py' if args.command == 'chat' else 'train.py'))]
    if args.device:
        command += ['--device', args.device]
    if args.command == 'chat':
        if args.mode:
            command += ['--mode', args.mode]
        if args.checkpoint:
            command += ['--checkpoint', str(args.checkpoint.resolve())]
        return subprocess.call(command, cwd=ROOT)
    device = C.lay_thiet_bi(args.device)
    if C.RESUME_POLICY not in ('latest_valid', 'never'):
        raise ValueError('RESUME_POLICY phải là latest_valid hoặc never.')
    checkpoint, saved = None, None
    if args.checkpoint:
        checkpoint = args.checkpoint.resolve()
        saved = validate(checkpoint, expected_architecture())
    elif not args.new and not args.init_from and C.RESUME_POLICY == 'latest_valid':
        checkpoint, saved, skipped = discover(expected=expected_architecture(), stage=args.stage)
        for path, error in skipped:
            print(f'Bỏ qua {path}: {error}')
        if not checkpoint and skipped:
            raise ValueError('Có checkpoint nhưng không có bản tương thích. Kiểm tra cấu hình hoặc chủ động dùng --new.')
    if checkpoint and args.folder:
        raise ValueError('Resume không đọc dữ liệu mới. Dùng --init-from CHECKPOINT --folder THU_MUC.')
    stage = args.stage or (saved.get('stage', 'pretrain') if saved else 'pretrain')
    if saved and stage != saved.get('stage', 'pretrain'):
        raise ValueError('Không đổi giai đoạn khi resume. Dùng --init-from CHECKPOINT --stage sft.')
    if not checkpoint:
        folder = args.folder or ROOT / 'Hoc_BimBom/Du_Lieu_Huan_Luyen' / ('Chat_SFT' if stage == 'sft' else 'Pretrain')
        if args.init_from:
            validate(args.init_from, expected_architecture(), resume=False)
            command += ['--init-from', str(args.init_from.resolve())]
        if stage == 'sft':
            if not args.init_from:
                raise ValueError('Bắt đầu SFT bằng --stage sft --init-from CHECKPOINT sau Pretrain.')
            pairs = [read_approved(path) for path in folder.glob('*.json')]
            if len({(e['question'], e['answer']) for e in pairs}) < 2:
                raise ValueError('Cần ít nhất 2 cặp hỏi/đáp khác nhau đã duyệt trong Chat_SFT.')
        elif not documents(folder):
            raise ValueError(f'Chưa có dữ liệu. Thêm TXT/MD đã kiểm tra vào {folder}')
        command += ['--folder', str(folder.resolve())]
    if args.steps is None:
        with session_lock(ROOT, kind='waiting'):
            extra = int(read_input('Nhập số bước muốn huấn luyện thêm: ').strip())
    else:
        extra = args.steps
    if extra < 1:
        raise ValueError('Số bước phải là số nguyên dương.')
    previous = saved['step'] if saved else 0
    print(f'Device: {device}\nCheckpoint: {checkpoint or "học dữ liệu mới"}\nHuấn luyện thêm {extra} bước: {previous} → {previous + extra}', flush=True)
    if checkpoint:
        command += ['--resume', str(checkpoint)]
    command += ['--stage', stage, '--steps', str(previous + extra)]
    return subprocess.call(command, cwd=ROOT)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, OSError, EOFError) as error:
        raise SystemExit(f'Lỗi: {error}') from error
    except KeyboardInterrupt:
        raise SystemExit('\nĐã dừng theo yêu cầu.')
