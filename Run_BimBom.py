"""Bộ điều khiển chat/train/status/stop; chọn rõ cách học, không ngầm khởi tạo lại."""
import argparse
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
import torch
import Chinh_Che_Do as C
from Model_BimBomAI.pipeline import ROOT, documents, dataset_changes
from Model_BimBomAI.Ma_Nguon.checkpoint import discover, validate, find_best, optimizer_steps
from Model_BimBomAI.Ma_Nguon.memory import read_approved
from Model_BimBomAI.Ma_Nguon.document_reader import extract_document
from Model_BimBomAI.Ma_Nguon.duplicates import normalized
from Model_BimBomAI.Ma_Nguon.runtime import initialize, request_stop, wait_stopped, active_session, read_input, session_lock


def expected_architecture():
    return dict(context=C.CONTEXT_LENGTH, dim=C.MODEL_DIM, heads=C.MODEL_HEADS, layers=C.MODEL_LAYERS)


def previous_speed(path):
    try:
        lines = (Path(path).parent / 'metrics.jsonl').read_text(encoding='utf-8').splitlines()
        for line in reversed(lines):
            try:
                value = json.loads(line).get('steps_per_second', 0)
                if math.isfinite(value) and value > 0:
                    return value
            except (ValueError, TypeError):
                continue
    except OSError:
        pass
    return None


class TrainingCancelled(Exception):
    """Leave the training menu without starting a child process."""


class TrainingMenuBack(Exception):
    """Return to mode selection without starting training."""


def training_input(prompt):
    value = read_input(prompt).strip()
    if value.casefold() in ('0', 'thoat', 'thoát', 'exit', 'q'):
        raise TrainingCancelled()
    return value


def choose_training_steps(initial=None, confirmed=False):
    from train import check_step_budget, safety_config
    limits = safety_config()
    default = C.TRAIN_DEFAULT_ADDITIONAL_STEPS
    if type(default) is not int or default < 1:
        raise ValueError('TRAIN_DEFAULT_ADDITIONAL_STEPS phải là số nguyên dương.')
    default = min(default, limits['max_steps'])
    print(f'Số bước học THÊM: tối thiểu 1, tối đa {limits["max_steps"]:,}. '
          f'Từ {limits["warn_steps"]:,} bước cần xác nhận. Nhập số nguyên không có dấu phân cách; 0 = thoát.', flush=True)
    extra = initial
    while True:
        if extra is None:
            raw = training_input(f'Số bước học thêm [Enter = {default}; 0 = thoát]: ')
            try:
                extra = int(raw) if raw else default
            except ValueError:
                print('Vui lòng nhập số nguyên, ví dụ 200.', flush=True)
                continue
        try:
            check_step_budget(extra, confirmed=True)
        except ValueError as error:
            # Explicit command-line budgets remain strict, without waiting for input.
            if initial is not None:
                raise
            print(str(error), flush=True)
            extra = None
            continue
        if extra < limits['warn_steps'] or confirmed:
            return extra
        print(f'CẢNH BÁO: sắp học thêm {extra:,} bước; cần xác nhận số bước lớn.', flush=True)
        answer = training_input('Nhập HOC_TIEP để giữ số bước này, nhập số bước khác (ví dụ 200), hoặc 0 để thoát: ')
        if answer.upper() == 'HOC_TIEP':
            return extra
        try:
            replacement = int(answer)
            check_step_budget(replacement, confirmed=True)
        except ValueError:
            print(f'Chưa xác nhận. Nhập số nguyên từ 1 đến {limits["max_steps"]:,}, HOC_TIEP, hoặc 0 để thoát.', flush=True)
            continue
        extra = replacement
        print(f'Đã đổi số bước học thêm thành {extra:,}.', flush=True)


def training_command(args):
    interactive = not (args.new or args.init_from or args.checkpoint)
    while True:
        # A return to the menu must not retain a previously selected checkpoint/stage.
        attempt = argparse.Namespace(**vars(args))
        try:
            return build_training_command(attempt, interactive)
        except TrainingMenuBack:
            if not interactive:
                raise


def resume_choice(message, choices):
    print(message, flush=True)
    while True:
        choice = training_input('Lựa chọn: ')
        if choice == '9':
            raise TrainingMenuBack()
        if choice in choices:
            return choice
        print('Nhập một lựa chọn đã liệt kê; 0 để thoát.', flush=True)


def build_training_command(args, interactive):
    from train import safety_config
    limits = safety_config(getattr(args, 'early_stopping', None))
    checkpoint, saved = None, None
    selected = 'new' if args.new else ('init' if args.init_from else ('resume' if args.checkpoint else None))
    if selected is None:
        print('Chọn cách huấn luyện:\n1. Học tiếp tập cũ (resume)\n2. Tạo mô hình mới từ đầu\n3. Học tài liệu hiện tại, giữ trọng số đã có (init-from)\n0. Thoát\nCó tài liệu mới trong Hoc_BimBom: chọn 3. Phiên đang học dở: chọn 1.', flush=True)
        while True:
            choice = training_input('Nhập 0, 1, 2 hoặc 3: ')
            if choice in ('1', '2', '3'):
                break
            print('Lựa chọn không hợp lệ. Nhập 1, 2, 3 hoặc 0 để thoát.', flush=True)
        selected = {'1': 'resume', '2': 'new', '3': 'init'}[choice]
        if selected == 'init':
            source = training_input('Checkpoint nền [Enter = best; hoặc đường dẫn .pt; 0 = thoát]: ').strip('"')
            args.init_from = source or 'best'
    device = C.lay_thiet_bi(args.device)
    if selected == 'resume':
        if args.checkpoint and args.checkpoint != 'latest':
            checkpoint = Path(args.checkpoint).resolve()
            saved = validate(checkpoint, expected_architecture())
        else:
            checkpoint, saved, skipped = discover(expected=expected_architecture(), stage=args.stage)
            for path, error in skipped:
                print(f'Bỏ qua {path}: {error}')
            if checkpoint is None:
                raise ValueError('Không có checkpoint hợp lệ/tương thích để tiếp tục. Đã dừng; chỉ dùng --new khi muốn tạo mô hình mới.')
        if args.folder:
            raise ValueError('Resume dùng dữ liệu đã lưu. Học tập dữ liệu mới bằng --init-from CHECKPOINT --folder THU_MUC.')
        saved_stage = saved.get('stage', 'pretrain')
        if args.stage and args.stage != saved_stage:
            raise ValueError('Không đổi giai đoạn khi resume. Dùng --init-from để đổi.')
        exhausted = (limits['early_stopping'] and
                     saved.get('early_stopping', {}).get('bad_evals', 0) >= limits['patience'])
        if exhausted:
            print(f'Checkpoint đã đạt ngưỡng Early Stopping ({limits["patience"]} lần không cải thiện). '
                  'Resume sẽ dừng ngay; chưa khởi chạy huấn luyện.', flush=True)
            if not interactive:
                raise ValueError('Không tiếp tục phiên đã Early Stopping. Kiểm tra dữ liệu rồi dùng --init-from best để mở phiên mới.')
            resume_choice('3. Dùng best để học tập tài liệu hiện tại (optimizer mới)\n9. Quay lại menu\n0. Thoát', ('3',))
            selected = 'init'
        elif saved_stage == 'pretrain':
            try:
                changes = dataset_changes(ROOT / 'Hoc_BimBom', saved['manifest'])
            except (ValueError, OSError) as error:
                changes = {}
                print(f'Chưa kiểm tra được tài liệu hiện tại: {error}. Resume vẫn dùng dữ liệu trong checkpoint.', flush=True)
            if any(changes.values()):
                print(f'Tài liệu so với checkpoint: thêm {len(changes.get("added", []))}, '
                      f'sửa {len(changes.get("changed", []))}, thiếu/chuyển đi {len(changes.get("removed", []))}.', flush=True)
                print('Resume chỉ dùng tập đã lưu. File chuyển sang Da_Hoc cũng được tính là thiếu ở thư mục nguồn.', flush=True)
                if interactive and (changes.get('added') or changes.get('changed')):
                    choice = resume_choice('3. Dùng best để học tập tài liệu hiện tại\n1. Vẫn học tiếp tập cũ\n9. Quay lại menu\n0. Thoát', ('1', '3'))
                    if choice == '3':
                        selected = 'init'
                else:
                    print('Muốn nạp tài liệu hiện tại: dùng --init-from best.', flush=True)
        if selected == 'init':
            args.init_from = 'best'
            args.stage = args.stage or saved_stage
            checkpoint, saved = None, None
    if selected == 'init':
        if str(args.init_from) == 'best':
            latest, state, skipped = discover(expected=expected_architecture(), resume=False)
            best = find_best(latest, state) if latest else None
            if best is None:
                raise ValueError('Không tìm thấy checkpoint best đã xác minh. Hãy chỉ định đường dẫn .pt.')
            args.init_from = str(best[0])
            print(f'Đã chọn best: {best[0]} | validation loss={best[1]:.6f}. Điểm này thuộc tập dữ liệu cũ.', flush=True)
        else:
            validate(Path(args.init_from), expected_architecture(), resume=False)
    if checkpoint and args.folder:
        raise ValueError('Resume dùng dữ liệu đã lưu. Học tập dữ liệu mới bằng --init-from CHECKPOINT --folder THU_MUC.')
    stage = args.stage or (saved.get('stage', 'pretrain') if saved else 'pretrain')
    if saved and stage != saved.get('stage', 'pretrain'):
        raise ValueError('Không đổi giai đoạn khi resume. Dùng --init-from để đổi.')
    command = [sys.executable, '-B', str(ROOT / 'train.py'), '--device', str(device), '--stage', stage]
    if checkpoint:
        command += ['--resume', str(checkpoint)]
    else:
        folder = args.folder or ROOT / 'Hoc_BimBom/Du_Lieu_Huan_Luyen' / ('Chat_SFT' if stage == 'sft' else 'Pretrain')
        if selected == 'init':
            command += ['--init-from', str(Path(args.init_from).resolve())]
        if stage == 'sft':
            if selected != 'init':
                raise ValueError('SFT cần --init-from CHECKPOINT nền; không tạo trọng số mới.')
            pairs = [read_approved(path) for path in folder.glob('*.json')]
            if len({normalized(entry['question']).casefold() for entry in pairs}) < 2:
                raise ValueError('Cần ít nhất 2 câu hỏi khác nhau đã duyệt trong Chat_SFT; nhiều đáp án cho một câu hỏi chưa đủ.')
        else:
            count = len(documents(folder, auto_split=True))
            if not count:
                raise ValueError(f'Chưa có dữ liệu. Thêm tài liệu đã kiểm tra (TXT/MD, DOCX, PPTX, XLSX/XLS, CSV/TSV, PDF chữ...) vào {folder}')
            print(f'Dữ liệu hiện tại: {count} tài liệu khác nhau. Thư mục: {folder}', flush=True)
        command += ['--folder', str(folder.resolve())]
    previous = optimizer_steps(saved) if saved else 0
    if saved and previous != saved['step']:
        print(f'Checkpoint cũ ghi {saved["step"]} bước; optimizer thực tế hoàn thành {previous}. Không tính các lần bỏ qua.', flush=True)
    print(f'Đã hoàn thành trong trạng thái huấn luyện này: {previous:,} bước. Số nhập tiếp theo là số học THÊM, không phải tổng.', flush=True)
    extra = choose_training_steps(args.steps, args.confirm_large_run)
    source_label = str(checkpoint or args.init_from or 'TRỌNG SỐ MỚI — đã chọn rõ')
    print(f'Device: {device}\nCách học: {selected}\nNguồn: {source_label}\nĐã hoàn thành: {previous}; học thêm: {extra}; tổng mục tiêu: {previous+extra}', flush=True)
    print('Validation: ' + ('dừng sớm khi không cải thiện (stop).' if limits['early_stopping']
          else 'chỉ cảnh báo (warn), tiếp tục học đủ bước; best được lưu riêng.'), flush=True)
    settings = saved['settings'] if saved and 'settings' in saved else dict(batch=C.MICRO_BATCH_SIZE, accum=C.GRAD_ACCUM_STEPS, lr=C.LEARNING_RATE)
    print(f'Batch: {settings["batch"]}; tích lũy: {settings["accum"]}; learning rate: {settings["lr"]}. '
          + ('Giữ cấu hình trong checkpoint.' if saved else 'Dùng cấu hình hiện tại trong Chinh_Che_Do.py.'), flush=True)
    speed = previous_speed(checkpoint) if checkpoint else None
    if speed:
        print(f'Ước tính từ phiên trước: {extra/speed/60:.1f} phút ở {speed:.2f} bước/giây; thời gian thực tế có thể thay đổi.', flush=True)
    else:
        print('Chưa đủ số liệu ước tính; ETA sẽ được cập nhật từ tốc độ thực tế ở các lần đánh giá.', flush=True)
    if saved:
        best = find_best(checkpoint, saved)
        if best:
            print(f'Best trên cùng dữ liệu/tokenizer: {best[0]} | validation loss={best[1]:.6f}. Latest không đồng nghĩa best.', flush=True)
    command += ['--steps', str(previous + extra), '--confirm-large-run', '--early-stopping', 'stop' if limits['early_stopping'] else 'warn']
    return command


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    chat = sub.add_parser('chat')
    train = sub.add_parser('train')
    status = sub.add_parser('status')
    stop = sub.add_parser('stop', aliases=['tat'])
    read = sub.add_parser('read', help='Đọc thử một tài liệu, không huấn luyện')
    read.add_argument('name', choices=['bimbom'])
    read.add_argument('file', type=Path)
    read.add_argument('--output', type=Path, help='Xuất toàn bộ nội dung sang file TXT/MD mới, không ghi đè')
    read.add_argument('--preview-chars', type=int, default=6000)
    stop.add_argument('--wait', type=int, default=30)
    for parser in (chat, train, status, stop):
        parser.add_argument('name', choices=['bimbom'])
    for parser in (chat, train):
        parser.add_argument('--device', choices=['auto', 'cpu', 'cuda'])
    chat.add_argument('--mode', choices=['CHAT_ONLY', 'CHAT_MEMORY', 'CHAT_COLLECT_TRAIN'])
    chat.add_argument('--checkpoint', type=Path)
    train.add_argument('--steps', type=int, help='Số optimizer steps THÀNH CÔNG muốn học thêm')
    group = train.add_mutually_exclusive_group()
    group.add_argument('--new', action='store_true')
    group.add_argument('--checkpoint', '--resume', dest='checkpoint', nargs='?', const='latest', help='Đường dẫn hoặc bỏ trống để tiếp tục bản gần nhất')
    group.add_argument('--init-from', help='Đường dẫn checkpoint hoặc best; optimizer mới, dữ liệu mới')
    train.add_argument('--stage', choices=['pretrain', 'sft'])
    train.add_argument('--folder', type=Path)
    train.add_argument('--confirm-large-run', action='store_true')
    train.add_argument('--early-stopping', choices=['warn', 'stop'], help='warn: học đủ bước; stop: cho phép dừng sớm theo validation')
    status.add_argument('--json', action='store_true')
    args = p.parse_args(argv)
    if Path(sys.prefix).resolve() != (ROOT / 'Model_BimBomAI/.venv').resolve():
        p.error('Dùng run.cmd và môi trường Model_BimBomAI/.venv.')
    initialize()
    if args.command == 'read':
        if args.preview_chars < 1:
            p.error('--preview-chars phải > 0')
        result = extract_document(args.file)
        if args.output:
            if args.output.suffix.lower() not in ('.txt', '.md'):
                p.error('--output cần đuôi .txt hoặc .md')
            with args.output.open('x', encoding='utf-8') as handle:
                handle.write(result['text'])
            print(f'Đã xuất: {args.output.resolve()}')
        print(f'Nguồn: {args.file.resolve()} | {len(result["text"]):,} ký tự | Không chạy huấn luyện.')
        for notice in result['extraction_warnings']:
            print('Lưu ý: ' + notice)
        print(result['text'][:args.preview_chars])
        if len(result['text']) > args.preview_chars:
            print(f'[Chỉ hiển thị {args.preview_chars:,}/{len(result["text"]):,} ký tự. Dùng --output để xuất toàn bộ.]')
        return 0
    if args.command in ('stop', 'tat'):
        if args.wait < 0:
            p.error('--wait phải >= 0')
        session = request_stop(ROOT)
        if session is None:
            print('BimBom hiện không chạy.')
            return 0
        print(f'Đã yêu cầu tắt phiên {session["kind"]}; train sẽ lưu checkpoint an toàn.', flush=True)
        if wait_stopped(session['id'], args.wait, ROOT):
            print('Phiên BimBom đã kết thúc.')
            return 0
        print('Phiên chưa kết thúc; yêu cầu tắt vẫn có hiệu lực. Xem run status bimbom.')
        return 2
    if args.command == 'status':
        checkpoint, saved, skipped = discover(expected=expected_architecture())
        best = find_best(checkpoint, saved) if saved else None
        changes, document_count, document_error = None, None, None
        try:
            current = documents(ROOT / 'Hoc_BimBom')
            document_count = len(current)
            if saved and saved.get('stage', 'pretrain') == 'pretrain':
                changes = dataset_changes(ROOT / 'Hoc_BimBom', saved['manifest'], current_documents=current)
        except (ValueError, OSError) as error:
            document_error = str(error)
        result = dict(python=platform.python_version(), executable=sys.executable, torch=str(torch.__version__),
                      cuda_available=torch.cuda.is_available(), gpu=torch.cuda.get_device_name() if torch.cuda.is_available() else None,
                      configured_device=C.CHE_DO, chat_mode=C.CHAT_MODE, active_session=active_session(ROOT),
                      checkpoint=str(checkpoint) if checkpoint else None, step=optimizer_steps(saved) if saved else 0,
                      legacy_reported_step=saved['step'] if saved else None,
                      best_checkpoint=str(best[0]) if best else None, best_validation_loss=best[1] if best else None,
                      stage=saved.get('stage', 'pretrain') if saved else None,
                      pretrain_documents=document_count, dataset_changes=changes, document_error=document_error,
                      pending=len(list((ROOT / 'Hoc_BimBom/Cho_Duyet').glob('*.json'))),
                      approved_sft=len(list((ROOT / 'Hoc_BimBom/Du_Lieu_Huan_Luyen/Chat_SFT').glob('*.json'))),
                      memories=len(list((ROOT / 'Bo_Nho_BimBom/Dai_Han').glob('*.json'))), skipped_checkpoints=skipped)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == 'chat':
        command = [sys.executable, '-B', str(ROOT / 'Chat_BimBom.py')]
        for name in ('device', 'mode', 'checkpoint'):
            value = getattr(args, name)
            if value:
                command += ['--' + name, str(value)]
        return subprocess.call(command, cwd=ROOT)
    try:
        with session_lock(ROOT, kind='waiting'):
            command = training_command(args)
    except (TrainingCancelled, EOFError):
        print('Đã thoát. Không bắt đầu huấn luyện.', flush=True)
        return 0
    return subprocess.call(command, cwd=ROOT)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, OSError, EOFError) as error:
        raise SystemExit(f'Lỗi: {error}') from error
    except KeyboardInterrupt:
        raise SystemExit('Đã hủy yêu cầu từ bộ chạy.')
