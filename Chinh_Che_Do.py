"""Cấu hình chung cho train.py và chat.py; sửa các giá trị bên dưới."""
CHE_DO = "auto"  # cpu | cuda | auto
CHAT_MODE = "CHAT_MEMORY"  # CHAT_ONLY | CHAT_MEMORY | CHAT_COLLECT_TRAIN
MAX_CONTEXT_TOKENS = 256
MAX_NEW_TOKENS = 100
TEMPERATURE = 0.8
RESUME_POLICY = "latest_valid"  # latest_valid | never
MEMORY_REQUIRES_CONFIRMATION = True
LOG_CHAT = True
MODEL_LAYERS = 4
MODEL_DIM = 256
MODEL_HEADS = 4
VOCAB_SIZE = 8000  # giới hạn trên; dữ liệu nhỏ có thể tạo ít token hơn
CONTEXT_LENGTH = 256
MICRO_BATCH_SIZE = 2
GRAD_ACCUM_STEPS = 16
LEARNING_RATE = 3e-4
CHECKPOINT_EVERY_STEPS = 200
USE_FP16 = True  # chỉ bật khi dùng CUDA
SEED = 42


def lay_thiet_bi(mode=None):
    import torch
    mode = (mode or CHE_DO).strip().lower()
    if mode not in {"cpu", "cuda", "auto"}:
        raise ValueError("CHE_DO phải là cpu, cuda hoặc auto")
    if mode == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("Đã chọn CUDA nhưng PyTorch không nhận GPU. Chạy kiem_tra.py và setup.ps1 -Backend cuda.")
    return torch.device("cuda" if mode != "cpu" and torch.cuda.is_available() else "cpu")

