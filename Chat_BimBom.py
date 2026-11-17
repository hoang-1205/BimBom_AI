"""Chat with a local model and explicitly confirmed, persistent memory."""
import argparse
import uuid
from pathlib import Path
import torch
import Chinh_Che_Do as C
from Model_BimBomAI.pipeline import load_model
from Model_BimBomAI.Ma_Nguon.checkpoint import discover, validate
from Model_BimBomAI.Ma_Nguon.inference import answer
from Model_BimBomAI.Ma_Nguon.memory import MemoryStore
from Model_BimBomAI.Ma_Nguon.runtime import ROOT, initialize, now, atomic_json, append_json, session_lock, read_input

HELP = '''/remember NỘI DUNG       Lưu ghi nhớ sau xác nhận
/rule NỘI DUNG           Lưu quy tắc trả lời sau xác nhận
/workflow NỘI DUNG       Lưu quy trình sau xác nhận
/memories               Xem ID và nội dung ghi nhớ
/edit ID NỘI DUNG        Sửa một ghi nhớ
/forget ID               Xóa một ghi nhớ
/correct CÂU TRẢ LỜI     Đưa đáp án sửa cho câu hỏi gần nhất vào hàng chờ
/pending                Xem các cặp hỏi/đáp chờ duyệt
/approve ID              Duyệt và xuất cặp hỏi/đáp cho SFT
/reject ID               Xóa bản nháp
/help                    Xem lệnh
/exit                    Thoát (cũng nhận /thoat, /stop, /tat)
/correct, /approve, /reject chỉ dùng trong CHAT_COLLECT_TRAIN.'''


def chat_session(checkpoint=None, device=None, mode=None, input_fn=read_input, output=print, root=ROOT):
    mode = mode or C.CHAT_MODE
    if mode not in ('CHAT_ONLY', 'CHAT_MEMORY', 'CHAT_COLLECT_TRAIN'):
        raise ValueError('CHAT_MODE không hợp lệ.')
    initialize(root)
    store = MemoryStore(root)
    device = C.lay_thiet_bi(device)
    model, tokenizer = None, None
    if checkpoint:
        model, tokenizer, _ = load_model(checkpoint, device)
    torch.set_num_threads(4)
    session = uuid.uuid4().hex
    history, last_question = [], ''
    output(f'BimBom_AI | {mode} | thiết bị: {device} | /help để xem lệnh')
    if model is None:
        output('Chưa có checkpoint. Có thể nhập/lưu ghi nhớ; chưa thể sinh câu trả lời bằng mô hình.')
    else:
        output(f'Checkpoint: {checkpoint}\nCâu trả lời do mô hình sinh có thể sai; bộ nhớ không cập nhật trọng số.')

    def confirmed(text):
        output(text)
        return not C.MEMORY_REQUIRES_CONFIRMATION or input_fn('Xác nhận [y/N]: ').strip().casefold() in ('y', 'yes', 'có', 'co')

    while True:
        try:
            message = input_fn('Bạn > ').strip()
            if not message:
                continue
            command, _, payload = message.partition(' ')
            if command in ('/exit', '/thoat', '/stop', '/tat'):
                break
            if command == '/help':
                output(HELP)
                continue
            if command == '/memories':
                entries = store.entries()
                for entry in entries:
                    output(f"{entry['id']} [{entry['kind']}] {entry['text']} | nguồn: {entry['source']}")
                if not entries:
                    output('Chưa có ghi nhớ.')
                continue
            if command == '/pending':
                drafts = store.drafts()
                for entry in drafts:
                    output(f"{entry['id']}\nHỏi: {entry['question']}\nĐáp: {entry['answer']}")
                if not drafts:
                    output('Không có bản nháp chờ duyệt.')
                continue
            if command.startswith('/'):
                if mode == 'CHAT_ONLY':
                    output('CHAT_ONLY không thay đổi bộ nhớ hoặc dữ liệu học. Đổi CHAT_MODE để dạy AI.')
                    continue
                if command in ('/remember', '/rule', '/workflow'):
                    if not payload.strip():
                        raise ValueError('Hãy nhập nội dung cần lưu.')
                    if confirmed('Lưu vào bộ nhớ: ' + payload):
                        identifier = store.remember(payload, session, {'/remember': 'fact', '/rule': 'rule', '/workflow': 'workflow'}[command])
                        output(f'Đã lưu ghi nhớ {identifier}. Trọng số chưa thay đổi.')
                elif command == '/edit':
                    identifier, _, text = payload.partition(' ')
                    if confirmed(f'Sửa {identifier} thành: {text}'):
                        store.update(identifier, text)
                        output('Đã sửa ghi nhớ.')
                elif command == '/forget':
                    if confirmed('Xóa ghi nhớ: ' + payload):
                        store.forget(payload)
                        output('Đã xóa ghi nhớ; transcript và checkpoint đã huấn luyện không thay đổi.')
                elif command in ('/correct', '/approve', '/reject'):
                    if mode != 'CHAT_COLLECT_TRAIN':
                        output('Đổi CHAT_MODE = "CHAT_COLLECT_TRAIN" hoặc thêm --mode CHAT_COLLECT_TRAIN để duyệt dữ liệu học.')
                        continue
                    if command == '/correct':
                        identifier = store.correct(last_question, payload, session)
                        output(f'Đã lưu bản nháp {identifier}; chưa đưa vào huấn luyện. Dùng /approve {identifier} sau khi kiểm tra.')
                    elif command == '/approve':
                        entries = {e['id']: e for e in store.drafts()}
                        if payload not in entries:
                            raise ValueError('Không tìm thấy ID bản nháp.')
                        entry = entries[payload]
                        if confirmed(f"Duyệt cặp:\nHỏi: {entry['question']}\nĐáp: {entry['answer']}"):
                            store.approve(payload)
                            output('Đã duyệt và xuất Chat_SFT. Chưa chạy huấn luyện.')
                    elif confirmed('Xóa bản nháp: ' + payload):
                        store.reject(payload)
                        output('Đã xóa bản nháp.')
                else:
                    output('Lệnh không tồn tại. Dùng /help.')
                continue
            last_question = message
            memories = store.relevant(message)
            if model is None:
                response = ('Ghi nhớ đã xác nhận (trích nguyên văn, không phải câu trả lời sinh):\n'
                            + '\n'.join(e['text'] for e in memories)) if memories else 'Chưa có mô hình đã huấn luyện để trả lời.'
            else:
                response = answer(model, tokenizer, message, memories, history, C.MAX_NEW_TOKENS,
                                  C.TEMPERATURE, device, C.MAX_CONTEXT_TOKENS)
            output('BimBom_AI > ' + response)
            history.append(dict(question=message, answer=response))
            history = history[-10:]
            if C.LOG_CHAT:
                event = dict(time=now(), session=session, question=message, answer=response,
                             checkpoint=str(checkpoint) if checkpoint else None, generated=model is not None)
                # Raw transcript is never selected by the training data reader.
                append_json(root / 'Hoc_BimBom/Hoi_Thoai_Goc' / (session + '.jsonl'), event)
                append_json(root / 'Ket_Qua/Nhat_Ky_Chat' / (session + '.jsonl'), event)
                atomic_json(root / 'Bo_Nho_BimBom/Ngan_Han' / (session + '.json'), history)
        except (EOFError, KeyboardInterrupt):
            output('\nĐã kết thúc phiên chat.')
            break
        except (ValueError, KeyError, OSError) as error:
            output(f'Lỗi thao tác/lưu dữ liệu: {error}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--device', choices=['auto', 'cpu', 'cuda'])
    parser.add_argument('--mode', choices=['CHAT_ONLY', 'CHAT_MEMORY', 'CHAT_COLLECT_TRAIN'])
    args = parser.parse_args()
    try:
        with session_lock(kind='chat'):
            if args.checkpoint:
                validate(args.checkpoint, resume=False)
                checkpoint = args.checkpoint
            else:
                checkpoint, _, skipped = discover(resume=False)
                for path, error in skipped:
                    print(f'Bỏ qua checkpoint {path}: {error}')
            chat_session(checkpoint, args.device, args.mode)
    except (ValueError, RuntimeError, OSError) as error:
        raise SystemExit(f'Lỗi: {error}') from error


if __name__ == '__main__':
    main()
