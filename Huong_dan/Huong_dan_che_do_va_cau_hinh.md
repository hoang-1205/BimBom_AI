# Hướng dẫn chỉnh chế độ và cấu hình BimBom AI

[Giới thiệu](GIOI_THIEU.md) | [Cách sử dụng](CACH_SU_DUNG.md)

Tệp cấu hình: [Chinh_Che_Do.py](../Chinh_Che_Do.py), tại `D:\BimBom_AI\Chinh_Che_Do.py`.

Các giá trị bên dưới là cấu hình hiện tại khi viết hướng dẫn. Tài liệu này không tự thay đổi cấu hình của AI.

## 1. Cách chỉnh và áp dụng

1. Từ cửa sổ PowerShell khác, chạy `run stop bimbom` và đợi phiên hiện tại kết thúc. Nếu đang train, chương trình hoàn tất bước hiện tại và lưu checkpoint trước khi dừng.
2. Mở `Chinh_Che_Do.py` bằng trình soạn thảo văn bản.
3. Sửa giá trị bên phải dấu `=` rồi lưu tệp. Giữ dấu ngoặc kép cho chuỗi; viết `True`/`False` đúng chữ hoa đầu.
4. Mở lại chat hoặc train để áp dụng. Riêng resume sẽ dùng thông số huấn luyện trong checkpoint, xem mục 7.

Nếu PowerShell chưa nhận lệnh `run`, dùng:

```powershell
cd D:\BimBom_AI
.\run.cmd stop bimbom
.\run.cmd status bimbom
```

Các lệnh PowerShell trong hướng dẫn được chạy tại thư mục dự án. Lệnh bắt đầu bằng `/` được nhập bên trong cửa sổ chat.

## 2. Chọn CPU hoặc GPU

```python
CHE_DO = "auto"
```

| Giá trị | Hoạt động |
| --- | --- |
| `"auto"` | Ưu tiên GPU CUDA; không có thì dùng CPU. |
| `"cuda"` | Bắt buộc dùng GPU NVIDIA qua CUDA; không khả dụng thì báo lỗi. |
| `"cpu"` | Chỉ dùng CPU. |

Có thể chọn thiết bị cho một lần chạy mà không sửa tệp:

```powershell
run chat bimbom --device cuda
```

Hoặc khi huấn luyện:

```powershell
run train bimbom --device cpu --steps 100
```

Chat và train chạy lần lượt. Chọn CPU không có nghĩa là giảm tổng thời gian xử lý; tốc độ phụ thuộc phần cứng và mô hình.

## 3. Chọn chế độ chat và học qua hội thoại

```python
CHAT_MODE = "CHAT_MEMORY"
```

| Chế độ | Chức năng |
| --- | --- |
| `"CHAT_ONLY"` | Chat và đọc ghi nhớ có sẵn; không thêm/sửa/xóa bộ nhớ hoặc dữ liệu học. |
| `"CHAT_MEMORY"` | Chat, lưu/sửa/xóa ghi nhớ sau xác nhận. Đây là mặc định. |
| `"CHAT_COLLECT_TRAIN"` | Có thêm `/correct`, `/approve`, `/reject` để chuẩn bị dữ liệu hỏi–đáp đã duyệt. |

Ví dụ mở riêng một phiên để dạy AI:

```powershell
run chat bimbom --mode CHAT_COLLECT_TRAIN --device cuda
```

Trong chat, `/remember` lưu kiến thức, `/rule` lưu quy tắc và `/workflow` lưu quy trình. Lưu bộ nhớ hoặc duyệt ví dụ **chưa cập nhật trọng số**. Muốn cập nhật trọng số phải chạy huấn luyện.

Hai tùy chọn liên quan:

```python
MEMORY_REQUIRES_CONFIRMATION = True
LOG_CHAT = True
```

- `MEMORY_REQUIRES_CONFIRMATION = True`: yêu cầu xác nhận trước các thao tác lưu/sửa/xóa hoặc duyệt có bước xác nhận. Đặt `False` bỏ câu hỏi xác nhận đó, nhưng vẫn phải chủ động dùng lệnh; không tự duyệt mọi hội thoại.
- `LOG_CHAT = True`: lưu transcript, nhật ký và ngữ cảnh phiên. Đặt `False` để ngừng lưu những dữ liệu này cho lượt mới; không xóa nhật ký cũ và không vô hiệu hóa lệnh lưu bộ nhớ.

## 4. Điều chỉnh mức xử lý khi chat

```python
MAX_CONTEXT_TOKENS = 256
MAX_NEW_TOKENS = 100
TEMPERATURE = 0.8
```

| Thông số | Ý nghĩa | Khi giảm |
| --- | --- | --- |
| `MAX_CONTEXT_TOKENS` | Số token ngữ cảnh tối đa được dùng khi sinh câu trả lời. | Ít nội dung được xét hơn, giảm phần ngữ cảnh xử lý. |
| `MAX_NEW_TOKENS` | Số token mới tối đa được sinh trong một lượt. | Giới hạn câu trả lời ngắn hơn và lượng công việc sinh văn bản tối đa. |
| `TEMPERATURE` | Độ ngẫu nhiên khi chọn token. | Thường làm lựa chọn ít ngẫu nhiên hơn; không bảo đảm câu trả lời đúng hơn. |

Token là đơn vị văn bản, không tương đương một từ. `MAX_CONTEXT_TOKENS` phải từ 8 trở lên; số token sinh và temperature phải dương. Ngữ cảnh thực tế còn bị giới hạn bởi kiến trúc mô hình đã lưu.

Ví dụ muốn giới hạn chat ngắn hơn:

```python
MAX_CONTEXT_TOKENS = 128
MAX_NEW_TOKENS = 50
TEMPERATURE = 0.8
```

Tăng giới hạn không tự làm mô hình thông minh hơn. Giảm context có thể khiến AI không xét được đủ ghi nhớ hoặc hội thoại trước đó.

## 5. Điều chỉnh mức tải khi huấn luyện

```python
MICRO_BATCH_SIZE = 2
GRAD_ACCUM_STEPS = 16
LEARNING_RATE = 1e-4
CHECKPOINT_EVERY_STEPS = 200
USE_FP16 = True
```

| Thông số | Tác dụng |
| --- | --- |
| `MICRO_BATCH_SIZE` | Số đoạn xử lý cùng lúc. Giảm từ `2` xuống `1` thường giảm nhu cầu VRAM. |
| `GRAD_ACCUM_STEPS` | Số lượt tích lũy gradient trước một lần cập nhật trọng số. Tăng giá trị làm mỗi bước cập nhật cần nhiều lượt xử lý hơn. |
| `LEARNING_RATE` | Mức điều chỉnh trọng số. `1e-4` nghĩa là `0.0001`; không nên tăng chỉ để mong học nhanh hơn. |
| `CHECKPOINT_EVERY_STEPS` | Khoảng cách lưu checkpoint. Giảm từ `200` xuống `100` để lưu thường xuyên hơn, tốn thêm ghi đĩa và dung lượng. |
| `USE_FP16` | Bật tính toán FP16 khi dùng CUDA. CPU vẫn dùng FP32. |

Cấu hình hiện tại xử lý **2 × 16 = 32 đoạn cho mỗi bước cập nhật**. Nếu đổi batch thành `1` và giữ tích lũy `16`, con số này còn 16. Nếu đổi batch thành `1` và tích lũy thành `32`, vẫn giữ 32 đoạn mỗi bước nhưng phải xử lý tuần tự nhiều lượt hơn; không bảo đảm tốc độ bằng cấu hình cũ.

Ví dụ giảm nhu cầu VRAM cho lần học mới:

```python
MICRO_BATCH_SIZE = 1
GRAD_ACCUM_STEPS = 16
USE_FP16 = True
```

Chương trình hiện **không có tùy chọn giới hạn GPU ở 50% hoặc 80% công suất**. Giảm batch chủ yếu điều chỉnh bộ nhớ và cách chia công việc, không bảo đảm giảm điện năng hoặc mức sử dụng GPU theo tỷ lệ tương ứng.

Nếu gặp lỗi hết VRAM, dừng phiên rồi kiểm tra batch/context. Nếu FP16 phát sinh lỗi số học, có thể thử `USE_FP16 = False` cho lần học với cấu hình mới, nhưng cần theo dõi mức dùng bộ nhớ. Các thay đổi này không tự ghi đè thông số trong checkpoint resume.

## 6. Chọn số bước muốn học thêm

```powershell
run train bimbom --steps 100
```

Lệnh trên học **thêm 100 bước**. Nếu checkpoint đang ở bước 200, bộ chạy đặt mục tiêu tổng là 300. Không ghi `--steps` thì chương trình hỏi số bước.

Nhiều bước hơn thường mất nhiều thời gian hơn, nhưng không bảo đảm chất lượng tốt hơn. Cần xem loss, mẫu sinh và kết quả trên câu hỏi độc lập.

Tắt từ PowerShell khác để lưu checkpoint rồi dừng:

```powershell
run stop bimbom
```

`run tat bimbom` có cùng chức năng. Trong chat có thể dùng `/tat` hoặc `/exit`. Ctrl+C một lần khi train yêu cầu lưu rồi dừng; lần thứ hai buộc dừng và có thể mất phần chưa lưu.

Lưu ý: `--steps` của lệnh trực tiếp `python train.py` là **tổng số bước cần đạt**, khác với số bước bổ sung của `run train bimbom`.

## 7. Khi đã có checkpoint, thay đổi nào được áp dụng?

| Cách chạy | Trọng số và tokenizer | Thông số huấn luyện | Dữ liệu |
| --- | --- | --- | --- |
| `run train bimbom --resume` | Khôi phục checkpoint tương thích. | Dùng thông số, optimizer và số bước đã lưu. | Dùng dữ liệu đã lưu trong checkpoint. |
| `run train bimbom --init-from ...` | Giữ trọng số và tokenizer từ checkpoint. | Đọc thông số huấn luyện hiện tại, tạo optimizer mới, đếm bước từ 0. | Đọc lại tập dữ liệu được chọn. |
| `run train bimbom --new` | Khởi tạo mới cho Pretrain. | Dùng cấu hình hiện tại. | Đọc tập Pretrain hiện tại. |

Muốn giữ trọng số nhưng áp dụng batch hoặc learning rate mới, dùng:

```powershell
run train bimbom --stage pretrain --init-from "DUONG_DAN_CHECKPOINT.pt" --steps 100
```

Thay `DUONG_DAN_CHECKPOINT.pt` bằng đường dẫn thật, có thể xem trường `checkpoint` trong `run status bimbom`. Lệnh này đọc văn bản Pretrain hiện tại; hãy chuẩn bị dữ liệu trước. Nếu muốn học cặp hỏi–đáp đã duyệt, dùng `--stage sft` thay cho `--stage pretrain`.

Khi không chỉ định cờ, `run train bimbom` mở menu chọn resume, tạo mới hoặc init-from. Dùng `--resume` để yêu cầu học tiếp; không có checkpoint hợp lệ thì chương trình dừng. RESUME_POLICY cũ không còn được sử dụng.

## 8. Các thông số kiến trúc cần giữ ổn định

```python
MODEL_LAYERS = 4
MODEL_DIM = 256
MODEL_HEADS = 4
VOCAB_SIZE = 8000
CONTEXT_LENGTH = 256
SEED = 42
```

- `MODEL_LAYERS`: số lớp Transformer.
- `MODEL_DIM`: kích thước biểu diễn; phải chia hết cho `MODEL_HEADS`.
- `MODEL_HEADS`: số đầu attention.
- `VOCAB_SIZE`: giới hạn từ vựng khi học tokenizer mới; dữ liệu nhỏ có thể tạo ít token hơn.
- `CONTEXT_LENGTH`: giới hạn ngữ cảnh của kiến trúc mô hình.
- `SEED`: hạt giống khởi tạo ngẫu nhiên cho lần học mới; không bảo đảm kết quả giống tuyệt đối giữa mọi thiết bị hoặc phiên bản thư viện.

Giữ nguyên `MODEL_LAYERS`, `MODEL_DIM`, `MODEL_HEADS`, `CONTEXT_LENGTH` nếu muốn tiếp tục dùng checkpoint cũ qua bộ chạy. Đổi các giá trị này có thể khiến kiểm tra tương thích từ chối checkpoint; `--init-from` cũng không chuyển đổi kiến trúc cho bạn.

`VOCAB_SIZE` chỉ dùng khi tạo tokenizer mới. Resume hoặc `--init-from` giữ tokenizer của checkpoint. Kiến trúc lớn hơn cần nhiều tài nguyên hơn; không phải cách tự động tăng chất lượng AI.

## 9. Kiểm tra sau khi chỉnh

```powershell
cd D:\BimBom_AI
.\run.cmd status bimbom
```

Lệnh hiển thị thiết bị, chế độ chat, phiên đang chạy và checkpoint tương thích; không chạy huấn luyện. Nó không in đầy đủ mọi tham số batch/context. Xem `Chinh_Che_Do.py` để kiểm tra giá trị vừa sửa và cấu hình được in khi bắt đầu train để biết lần học thực sự dùng thông số nào.

Nếu có lỗi cú pháp sau khi sửa, kiểm tra dấu ngoặc kép, dấu `=` và cách viết `True`/`False`. Nếu checkpoint bị báo khác kiến trúc, khôi phục đúng các giá trị kiến trúc của checkpoint trước khi resume.

## 10. Các giới hạn huấn luyện mới

```python
EVAL_EVERY_STEPS = 100
EARLY_STOPPING_ENABLED = False  # warn: chỉ cảnh báo, vẫn tiếp tục tới mục tiêu
EARLY_STOPPING_PATIENCE = 4
EARLY_STOPPING_MIN_DELTA = 0.01
MAX_CONSECUTIVE_NONFINITE = 5
TRAIN_WARN_ADDITIONAL_STEPS = 10000
TRAIN_MAX_ADDITIONAL_STEPS = 100000
TRAIN_DEFAULT_ADDITIONAL_STEPS = 200  # Enter tại câu hỏi số bước của run train
MIN_TOKENS_PER_SPLIT = 32
```

Đánh giá mỗi 100 optimizer steps thành công. Mặc định chỉ cảnh báo khi validation không cải thiện đủ 0,01 sau 4 lần đánh giá; chỉ dừng theo ngưỡng này khi bật Early Stopping. Mọi mức validation thấp hơn vẫn được ghi nhận là best; ngưỡng 0,01 chỉ quyết định có đặt lại bộ đếm chờ hay không. Năm lần cập nhật NaN/Inf liên tiếp sẽ dừng an toàn. Các bước bị bỏ qua không tăng số bước đã học.

Từ 10.000 bước bổ sung, phải xác nhận `HOC_TIEP` hoặc chủ động dùng `--confirm-large-run`. Trên 100.000 bước bổ sung bị từ chối, kể cả có cờ xác nhận. Các giới hạn an toàn này được đọc ở mỗi phiên, bao gồm resume; batch, accumulation và learning rate khi resume vẫn lấy từ checkpoint.

Mỗi phần train/validation Pretrain phải có ít nhất 32 token nội dung; đây chỉ là mức tối thiểu kỹ thuật, không bảo đảm chất lượng đánh giá. Một file đủ dài được chia thành hai đoạn không chồng lặp. Tài liệu gốc không bị sửa.

Chi tiết và kiểm thử: [Huấn luyện an toàn](HUAN_LUYEN_AN_TOAN.md).

## Tự chia file lớn

Đã bật `AUTO_SPLIT_LARGE_FILES`: file CSV/TSV/văn bản lớn hơn 16 MiB được chuẩn bị từng phần khoảng 2 triệu ký tự, tối đa 2 phần chờ mỗi nguồn. File gốc được giữ nguyên. Chọn **3** khi chạy `run train bimbom` để học tài liệu hiện tại và nhận phần tiếp theo; resume giữ tập dữ liệu cũ. Xem [cấu hình và hướng dẫn tự chia dữ liệu](TU_CHIA_DU_LIEU.md).
