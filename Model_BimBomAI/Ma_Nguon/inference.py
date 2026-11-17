"""Context budgeting and response-only generation for interactive chat."""
import torch
from .runtime import check_stop


def build_context(tokenizer, question, memories, history, limit):
    if limit < 8:
        raise ValueError('MAX_CONTEXT_TOKENS phải >= 8.')
    suffix = tokenizer.encode('\nTrả lời:').ids
    current = tokenizer.encode('Câu hỏi: ' + question).ids
    current = current[-max(1, limit - len(suffix)):]
    tail = current + suffix
    room = max(0, limit - len(tail))
    memory = '\n'.join('Ghi nhớ đã xác nhận: ' + e['text'] for e in memories)
    memory_ids = tokenizer.encode(memory + '\n').ids[:room] if memory else []
    room -= len(memory_ids)
    past = '\n'.join(f"Câu hỏi: {h['question']}\nTrả lời: {h['answer']}" for h in history)
    history_ids = tokenizer.encode(past + '\n').ids[-room:] if past and room else []
    return (memory_ids + history_ids + tail)[-limit:]


@torch.no_grad()
def answer(model, tokenizer, question, memories, history, count, temperature, device, max_context):
    if count < 1 or temperature <= 0:
        raise ValueError('Số token và temperature phải dương.')
    model.eval()
    limit = min(max_context, model.context)
    ids = build_context(tokenizer, question, memories, history, limit)
    generated = []
    for _ in range(count):
        check_stop()
        logits = model(torch.tensor([ids[-limit:]], device=device))[0, -1].float()
        token = torch.multinomial((logits / temperature).softmax(-1), 1).item()
        if token == tokenizer.token_to_id('[EOS]'):
            break
        generated.append(token)
        ids.append(token)
    return tokenizer.decode(generated).strip() or '[Mô hình kết thúc lượt mà chưa sinh nội dung.]'
