"""Sinh tiếp văn bản hoặc tra cứu có nguồn bằng BimBom v2."""
import argparse
from pathlib import Path
import torch
import Chinh_Che_Do as C
from Model_BimBomAI.pipeline import load_model, generate
from Model_BimBomAI.ky_nang import search, save_draft
from Model_BimBomAI.bo_nho import retrieve
from Model_BimBomAI.bao_cao import save_review
from Model_BimBomAI.Ma_Nguon.runtime import session_lock, read_input, check_stop


def legacy_main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint', type=Path)
    p.add_argument('--prompt')
    p.add_argument('--tokens', type=int, default=100)
    p.add_argument('--temperature', type=float, default=.8)
    p.add_argument('--device', choices=['cpu', 'cuda', 'auto'])
    p.add_argument('--rag', action='store_true')
    p.add_argument('--skills', action='store_true')
    p.add_argument('--save-draft', action='store_true')
    a = p.parse_args()
    if not a.checkpoint and not (a.rag or a.skills):
        p.error('Cần --checkpoint, --rag hoặc --skills')
    if a.tokens < 0 or a.temperature <= 0:
        p.error('tokens >= 0 và temperature > 0')
    torch.set_num_threads(4)
    device = C.lay_thiet_bi(a.device)
    print(f'Device: {device}')
    model, tokenizer, _ = load_model(a.checkpoint, device) if a.checkpoint else (None, None, None)
    def respond(question):
        check_stop()
        if a.skills:
            hits = search(question)
            result = '\n\n'.join(f"{'TRÙNG KHỚP' if exact else 'GỢI Ý CẦN KIỂM TRA'}\n{entry['answer']}\n{entry['workflow']}\nNguồn: {path}"
                                   for exact, score, path, entry in hits) or 'Không tìm thấy kỹ năng đã duyệt.'
        else:
            hits = retrieve(question) if a.rag else []
            refs = '\n\n'.join(f"[{i}] {h['text']}\nNguồn: {h['source']} (đoạn {h['chunk']})" for i, h in enumerate(hits, 1))
            if a.rag and not hits:
                result = 'Không tìm thấy tài liệu phù hợp; không tạo câu trả lời.'
            elif model:
                prompt = question
                if hits:
                    suffix = f'\nCâu hỏi: {question}\nTrả lời:'
                    room = max(0, model.context - len(tokenizer.encode(suffix).ids))
                    context_ids = tokenizer.encode('\n'.join(h['text'] for h in hits)).ids[:room]
                    prompt = tokenizer.decode(context_ids) + suffix
                result = generate(model, tokenizer, prompt, a.tokens, a.temperature, device)
                if hits:
                    result += '\n\nTÀI LIỆU TRA CỨU (cần kiểm tra câu sinh):\n' + refs
            else:
                result = refs
        print(result)
        mode = 'Kỹ năng đã duyệt' if a.skills else ('Tra cứu RAG' if a.rag else 'Sinh văn bản')
        source = f'Chế độ: {mode}\nCheckpoint: {a.checkpoint.resolve() if a.checkpoint else "Không dùng"}'
        try:
            print('Đã lưu để giáo viên kiểm tra:', save_review(question, result, source))
        except OSError as error:
            print(f'KHÔNG LƯU ĐƯỢC file Markdown: {error}. Hãy sao chép câu trả lời trên màn hình.')
        if a.save_draft:
            print('Bản nháp:', save_draft(question, result, source=str(a.checkpoint or 'retrieval')))
    if a.prompt is not None:
        respond(a.prompt)
    else:
        print('Nhập /thoat để kết thúc.')
        while True:
            try:
                question = read_input('Bạn: ').strip()
            except (EOFError, KeyboardInterrupt):
                break
            if question in ('/thoat', '/exit', '/stop', '/tat'):
                break
            if question:
                respond(question)


def main():
    try:
        with session_lock(kind='chat'):
            legacy_main()
    except (ValueError, RuntimeError, OSError) as error:
        raise SystemExit(f'Lỗi: {error}') from error


if __name__ == '__main__':
    main()

