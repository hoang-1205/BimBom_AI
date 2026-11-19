"""Cấu hình chung cho train.py và chat.py; sửa các giá trị bên dưới."""
CHE_DO = "auto"  # cpu | cuda | auto
CHAT_MODE = "CHAT_MEMORY"  # CHAT_ONLY | CHAT_MEMORY | CHAT_COLLECT_TRAIN
MAX_CONTEXT_TOKENS = 25600000000
MAX_NEW_TOKENS = 100
TEMPERATURE = 0.8
MEMORY_REQUIRES_CONFIRMATION = True
LOG_CHAT = True
MODEL_LAYERS = 4
MODEL_DIM = 256
MODEL_HEADS = 4
VOCAB_SIZE = 8000  # giới hạn trên; dữ liệu nhỏ có thể tạo ít token hơn
CONTEXT_LENGTH = 256
MICRO_BATCH_SIZE = 2
GRAD_ACCUM_STEPS = 16
LEARNING_RATE = 1e-4  # áp dụng cho lần mới/--init-from; resume giữ LR đã lưu
CHECKPOINT_EVERY_STEPS = 200
EVAL_EVERY_STEPS = 100
EARLY_STOPPING_ENABLED = False  # học đủ số bước; vẫn đánh giá, cảnh báo và giữ best
EARLY_STOPPING_PATIENCE = 4
EARLY_STOPPING_MIN_DELTA = 0.01
MAX_CONSECUTIVE_NONFINITE = 5
TRAIN_WARN_ADDITIONAL_STEPS = 10000
TRAIN_MAX_ADDITIONAL_STEPS = 100000
TRAIN_DEFAULT_ADDITIONAL_STEPS = 200  # Enter tại menu; chạy ngắn rồi xem chất lượng
MIN_TOKENS_PER_SPLIT = 32
DOCUMENT_TEXT_ENCODING = "auto"  # UTF-8 hoặc UTF-16/32 có BOM; có thể đặt cp1258
DOCUMENT_MAX_FILE_MB = 25600
DOCUMENT_MAX_ARCHIVE_MB = 51200
DOCUMENT_MAX_CHARACTERS = 60000000
DOCUMENT_MAX_CELLS = 2000000
DOCUMENT_READ_EXTENSIONLESS = True  # nhận văn bản UTF-8/UTF-16 không có đuôi, như en_sents
DOCUMENT_SKIP_INVALID = True  # báo và bỏ qua file lỗi khi đọc cả thư mục; đọc một file vẫn báo lỗi
IMPORT_MAX_TOTAL_FILE_MB = 25600  # tổng dung lượng nguồn được chọn mỗi lần; ưu tiên file nhỏ
IMPORT_MAX_TOTAL_CHARACTERS = 60000000  # file chưa được chọn vẫn ở Hoc_BimBom
TOKENIZER_CHUNK_CHARACTERS = 32768
TRAIN_MAX_DATA_TOKENS = 20000000  # tổng token train + validation; vượt thì tự chọn ít file/phần hơn
AUTO_SPLIT_LARGE_FILES = True  # Pretrain: chia CSV/TSV/văn bản lớn; giữ nguyên nguồn
AUTO_SPLIT_TRIGGER_MB = 16  # file lớn hơn ngưỡng này được chia, theo MiB
AUTO_SPLIT_PART_CHARACTERS = 2000000  # CSV giữ nguyên bản ghi nên có thể lớn hơn
AUTO_SPLIT_PENDING_PARTS = 2  # số phần tạo sẵn mỗi nguồn; dùng hết mới đọc tiếp
AUTO_SPLIT_MAX_RECORD_CHARACTERS = 8000000
AUTO_SPLIT_CSV_HAS_HEADER = True  # False nếu CSV không có tiêu đề; áp dụng hàng đợi mới
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

