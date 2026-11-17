# Cách sử dụng BimBom AI

[Giới thiệu](GIOI_THIEU.md) | [Phân tích hồ sơ và lệnh cũ](PHAN_TICH_VA_LENH_CU.md)

Các lệnh PowerShell bên dưới chạy tại `D:\BimBom_AI`, không phải tại thư mục hướng dẫn. Các lệnh bắt đầu bằng `/` được nhập bên trong cửa sổ chat.

## 1. Khởi chạy

Mở PowerShell và vào thư mục dự án:

```powershell
cd D:\BimBom_AI
```

Chọn lệnh phù hợp, không cần chạy tất cả cùng lúc:

| Muốn làm gì? | Lệnh tại thư mục dự án | Lệnh ngắn khi PATH đã nhận |
| --- | --- | --- |
| Kiểm tra trạng thái | `.\run.cmd status bimbom` | `run status bimbom` |
| Mở chat | `.\run.cmd chat bimbom` | `run chat bimbom` |
| Huấn luyện | `.\run.cmd train bimbom` | `run train bimbom` |
| Tắt phiên đang chạy | `.\run.cmd stop bimbom` | `run stop bimbom` hoặc `run tat bimbom` |

Chat và train chạy lần lượt. Muốn chuyển từ chat sang train, gõ `/tat` trong chat, sau đó chạy lệnh train ở PowerShell.

`run.cmd` dùng Python 3.13 tại `Model_BimBomAI\.venv`. Không cần kích hoạt venv hoặc cài Python thứ hai. Sau khi thư mục dự án được thêm vào PATH người dùng, mở terminal mới để dùng `run status bimbom`, `run chat bimbom`, `run train bimbom` từ thư mục bất kỳ. Nếu terminal cũ chưa nhận PATH, dùng đường dẫn đầy đủ `D:\BimBom_AI\run.cmd`.

`status` hiển thị Python, PyTorch, CUDA/GPU, checkpoint hợp lệ gần nhất, bước đã học và số bản ghi. Đọc `skipped_checkpoints` nếu có checkpoint hỏng hoặc khác kiến trúc.

### Tắt AI

Từ cửa sổ PowerShell khác, dùng `run stop bimbom` hoặc `run tat bimbom`. Chat dừng kể cả khi đang đợi nhập hoặc đang sinh câu trả lời. Train hoàn thành bước đang chạy, lưu checkpoint rồi dừng; nếu còn ở khâu chuẩn bị dữ liệu thì cần chờ khâu đó hoàn tất. Cửa sổ đang hỏi số bước cũng nhận lệnh tắt. Lệnh này không tắt máy tính.

Mặc định lệnh chờ tối đa 30 giây. Nếu chưa xong, yêu cầu tắt vẫn được giữ; xem `active_session` trong `run status bimbom` hoặc chờ lâu hơn bằng `run stop bimbom --wait 60`. Khi không có phiên chạy, lệnh báo rõ và không làm gì. Trong chat, `/stop`, `/tat`, `/exit` và `/thoat` đều kết thúc phiên.

Tắt không xóa checkpoint hoặc bộ nhớ. Khi học lại, bộ chạy tiếp tục từ checkpoint vừa lưu. Chỉ phiên BimBom giữ khóa hiện tại nhận yêu cầu tắt, không dừng các tiến trình Python khác.

## 2. Ba chế độ chat

Sửa `CHAT_MODE` trong `D:\BimBom_AI\Chinh_Che_Do.py`, lưu rồi mở lại phiên chat:

| Chế độ | Hoạt động |
| --- | --- |
| `CHAT_ONLY` | Chat và đọc ghi nhớ có sẵn, không sửa bộ nhớ hoặc dữ liệu học. |
| `CHAT_MEMORY` | Mặc định; thêm/sửa/xóa ghi nhớ sau xác nhận. |
| `CHAT_COLLECT_TRAIN` | Thêm hàng chờ sửa đáp án và duyệt xuất dữ liệu SFT. |

Có thể đổi cho riêng một phiên:

```powershell
.\run.cmd chat bimbom --mode CHAT_COLLECT_TRAIN
```

Chat tự chọn checkpoint tải được gần nhất. Chọn bản cụ thể bằng `--checkpoint "DUONG_DAN"`; thay `DUONG_DAN` bằng đường dẫn `.pt` thực tế. Khi chưa có checkpoint, giao diện báo rõ và chỉ cho quản lý/trích dẫn bộ nhớ. Khi có checkpoint, câu trả lời thực sự được sinh từ mô hình cục bộ; mô hình nhỏ hoặc chưa học đủ có thể trả lời vô nghĩa/sai.

## 3. Dạy và quản lý bộ nhớ

```text
/remember Tôi muốn câu trả lời bằng tiếng Việt.
Xác nhận [y/N]: y
/memories
/edit ID Nội dung thay thế
/forget ID
/rule Trình bày câu trả lời ngắn, rõ ràng.
/workflow Đọc yêu cầu, kiểm tra dữ liệu, rồi trình bày kết quả.
/help
/stop
```

Thay `ID` bằng mã trong `/memories`. Lưu, sửa, xóa đều yêu cầu xác nhận mặc định. Nội dung được ghi cùng nguồn phiên và thời gian, có chỉ mục từ khóa; phiên chat sau đọc lại ghi nhớ liên quan. Quy tắc và quy trình cũng xuất vào thư mục kỹ năng tương ứng. `/forget` xóa ghi nhớ và chỉ mục hiện tại; không tẩy nội dung khỏi transcript cũ hay trọng số đã được huấn luyện.

Đây là bộ nhớ trên đĩa, **không phải cập nhật trọng số**. Ghi nhớ được đưa vào ngữ cảnh có giới hạn; mô hình chưa chắc tuân thủ mọi quy tắc. Câu hỏi hiện tại được ưu tiên, sau đó ghi nhớ và phần hội thoại gần đây còn vừa context. Phiên mới không tự tải lại toàn bộ transcript cũ.

`LOG_CHAT = True` lưu hội thoại vào `Hoc_BimBom\Hoi_Thoai_Goc`, nhật ký vào `Ket_Qua\Nhat_Ky_Chat`, ngữ cảnh phiên vào `Bo_Nho_BimBom\Ngan_Han`. Đặt `LOG_CHAT = False` để không lưu các dữ liệu này cho các lượt mới. Tùy chọn này không xóa nhật ký cũ.

## 4. Duyệt cặp hỏi/đáp

Trong `CHAT_COLLECT_TRAIN`, nhập một câu hỏi, rồi:

```text
/correct Câu trả lời đúng đã được kiểm tra cho câu hỏi vừa nhập.
/pending
/approve ID
Xác nhận [y/N]: y
```

`/correct` chỉ tạo bản nháp tại `Hoc_BimBom\Cho_Duyet`. `/approve` hiển thị cả câu hỏi/đáp án, sau xác nhận mới xuất JSON vào `Du_Lieu_Huan_Luyen\Chat_SFT` và `Ky_Nang_BimBom_Hoc_Duoc\Vi_Du_Chuan`. `/reject ID` xóa bản nháp sau xác nhận. Không tự lấy câu trả lời do AI sinh làm dữ liệu đã duyệt.

Mỗi bản đã duyệt có dấu kiểm tra nội dung. Nếu sửa trực tiếp JSON sau khi duyệt, train sẽ từ chối; hãy tạo và duyệt lại ví dụ. Cần ít nhất 2 cặp khác nhau để tách train/validation. Duyệt không tự chạy GPU hoặc huấn luyện.

## 5. Pretrain từ đầu

1. Đặt tài liệu gốc trong `Hoc_BimBom\Tai_Lieu` nếu muốn giữ để biên tập.
2. Chuyển văn bản TXT/MD UTF-8 đã kiểm tra vào `Hoc_BimBom\Du_Lieu_Huan_Luyen\Pretrain`.
3. Chạy:

```powershell
.\run.cmd train bimbom
# Hoặc chỉ định số bước, không cần nhập tương tác:
.\run.cmd train bimbom --steps 100
```

Lần đầu tạo tokenizer và trọng số ngẫu nhiên. Lần sau tự chọn checkpoint hợp lệ gần nhất và học **thêm** số bước bạn nhập. Ví dụ đang ở bước 100, `--steps 200` trong `run.cmd` đạt tổng 300.

Để chủ động tạo mô hình mới, dùng `--new`. Mỗi lần tạo thư mục kết quả riêng; không xóa checkpoint cũ. `RESUME_POLICY = "never"` tắt tự tiếp tục; mặc định là `"latest_valid"`.

Không tự đọc `Tai_Lieu`, `Hoi_Thoai_Goc`, `Cho_Duyet` hay `Chat_SFT` như văn bản Pretrain. Lệnh cũ `train.py --folder .\Hoc_BimBom` được ánh xạ vào thư mục Pretrain. `--folder` có thể chọn tập TXT/MD khác do bạn chủ động chuẩn bị.

## 6. Resume và học dữ liệu mới

Trong các ví dụ bên dưới, thay `DUONG_DAN_CHECKPOINT` bằng đường dẫn `.pt` có thật, đặt trong dấu ngoặc kép nếu có khoảng trắng. Có thể xem đường dẫn ở trường `checkpoint` khi chạy `.\run.cmd status bimbom`. Nếu giá trị là `null`, hãy hoàn thành Pretrain trước.

```powershell
# Học thêm 200 bước từ checkpoint cụ thể:
.\run.cmd train bimbom --checkpoint DUONG_DAN_CHECKPOINT --steps 200

# Chuyển từ mô hình nền sang cặp chat đã duyệt:
.\run.cmd train bimbom --stage sft --init-from DUONG_DAN_CHECKPOINT --steps 100

# Học văn bản mới, giữ tokenizer/trọng số đã có:
.\run.cmd train bimbom --stage pretrain --init-from DUONG_DAN_CHECKPOINT --steps 100
```

`--checkpoint`/resume khôi phục đúng model, optimizer, scaler, RNG, tokenizer, dữ liệu và số bước đã lưu. Không nạp thêm tài liệu mới khi resume. `--init-from` giữ trọng số và tokenizer, đọc tập dữ liệu hiện tại, tạo optimizer mới và đếm bước từ 0 cho giai đoạn mới. SFT chỉ tính loss trên câu trả lời và token kết thúc, không tính loss trên câu hỏi. Không tự huấn luyện lại tokenizer khi chuyển SFT.

Sau lần SFT đầu, `run train bimbom` tiếp tục checkpoint SFT gần nhất. Nếu muốn tiếp tục một bản cụ thể, chỉ rõ `--checkpoint`.

Lệnh trực tiếp cũ vẫn dùng **TỔNG** bước, khác bộ chạy:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe train.py --resume DUONG_DAN_CHECKPOINT --steps 300 --device cuda
```

Checkpoint được kiểm tra định dạng, kiến trúc, tensor, tokenizer, optimizer, RNG, manifest và token/nhãn trước khi tiếp tục. Chỉ kiểm tra bằng tên file là không đủ. Checkpoint mới có dấu kiểm tra tokenizer và dữ liệu; checkpoint v2 cũ vẫn được hỗ trợ nếu cấu trúc hợp lệ. Không hỗ trợ checkpoint của kiến trúc khác hoặc lịch học tùy biến ngoài pipeline này. Pipeline hiện không dùng scheduler. Chuyển giữa CPU/CUDA hoặc thay phiên bản thư viện có thể làm kết quả số học khác nhau.

## 7. Thiết bị và kết quả

`CHE_DO = "auto"` ưu tiên CUDA, thiếu thì CPU. `"cuda"` bắt buộc GPU; `"cpu"` chỉ CPU. Có thể ghi đè bằng `--device cpu` hoặc `--device cuda`. Các chế độ chat và train/đánh giá dùng khóa hệ điều hành để không chạy đồng thời qua các lệnh được cung cấp. Khi tiến trình kết thúc hoặc bị tắt, hệ điều hành tự nhả khóa; không cần xóa `.session.lock`.

Cấu hình mặc định: 4 lớp, dim 256, 4 heads, context 256, micro-batch 2, tích lũy 16, FP16 trên CUDA, lưu mỗi 200 bước và bước cuối. `MAX_CONTEXT_TOKENS`, `MAX_NEW_TOKENS`, `TEMPERATURE` điều chỉnh suy luận. Giảm batch/context nếu thiếu VRAM; không tự chuyển CPU khi đang train CUDA.

Checkpoint và `best.json`, `latest.json`, cấu hình, loss, mẫu sinh được lưu trong `Ket_Qua\Checkpoint_BimBom\TEN_LAN`; nhật ký train trong `Ket_Qua\Nhat_Ky_Train`. Tokenizer theo từng lần nằm cùng dữ liệu đã xử lý và được nhúng trong checkpoint, tránh lấy nhầm tokenizer toàn cục. Checkpoint ghi qua file tạm rồi thay thế; giữ các checkpoint đã tạo, bao gồm gần nhất và tốt nhất từng lần. Đây là kết quả huấn luyện, không phải cơ chế sao lưu.

Ưu tiên `run stop bimbom` để lưu checkpoint trước khi dừng. Ctrl+C dừng học ngay; có thể mất các bước kể từ checkpoint gần nhất. Không tự xóa checkpoint hoặc log. Đánh giá thêm bằng câu hỏi độc lập; loss thấp không chứng minh AI biết trò chuyện hay tư vấn đúng.

## 8. Kiểm tra kỹ thuật

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe -B -m pip check
.\run.cmd status bimbom
```

`pip check` kiểm tra các thư viện phụ thuộc; `status` kiểm tra môi trường, thiết bị và checkpoint. Hai lệnh này không huấn luyện mô hình.

Thư mục kiểm thử đã được gỡ theo yêu cầu; không cần thư mục này để chạy chat/train. Các thư mục dữ liệu trống cần cho chat/train được giữ. Cấu hình thực tế ở `Chinh_Che_Do.py`, tokenizer nằm trong checkpoint và dữ liệu đã xử lý.

Nếu cần cài lại thư viện, dùng `Model_BimBomAI\setup.ps1 -Backend cuda` hoặc `-Backend cpu`; phiên bản thực tế trong `Model_BimBomAI\requirements.lock.txt`. Không tạo môi trường thứ hai. Đợt nâng cấp này không tạo bản sao lưu và không khôi phục dữ liệu đã xóa ở lần đặt lại.

## 9. Xử lý lỗi thường gặp

| Hiện tượng | Cách xử lý |
| --- | --- |
| PowerShell không nhận `run` | Mở terminal mới; hoặc `cd D:\BimBom_AI` rồi dùng `.\run.cmd ...`. |
| Chat báo chưa có checkpoint | Vẫn có thể dùng `/remember`. Muốn mô hình sinh câu trả lời, cần dữ liệu Pretrain và huấn luyện trước. |
| Train báo chưa có dữ liệu | Đặt TXT/MD có nội dung vào `Hoc_BimBom\Du_Lieu_Huan_Luyen\Pretrain`; tài liệu chỉ nằm trong `Tai_Lieu` chưa được dùng để train. |
| Báo có phiên BimBom khác | Dùng `run stop bimbom` từ PowerShell khác, đợi kết thúc rồi chạy lại. Không xóa `.session.lock`. |
| `/correct` hoặc `/approve` không dùng được | Thoát chat rồi mở lại với `--mode CHAT_COLLECT_TRAIN`. Nhập câu hỏi trước khi `/correct`. |
| SFT báo thiếu dữ liệu | Duyệt ít nhất 2 cặp hỏi/đáp khác nhau, và dùng checkpoint nền qua `--init-from`. |
| Có checkpoint nhưng không tương thích | Xem `skipped_checkpoints` và cấu hình kiến trúc; khôi phục cấu hình phù hợp. Chỉ dùng `--new` khi muốn tạo mô hình mới. |
| CUDA không khả dụng | Dùng `--device cpu` hoặc `CHE_DO = "auto"`; kiểm tra môi trường trước khi cài lại thư viện. |
| Hết VRAM | Tắt phiên đang dùng GPU; giảm micro-batch/context cho lần học mới. Resume giữ cấu hình đã lưu, sửa file cấu hình không tự đổi checkpoint cũ. |
| Lệnh tắt hết thời gian chờ | Yêu cầu vẫn có hiệu lực. Xem `active_session` trong status; có thể dùng `run stop bimbom --wait 60`. |
| Ghi bộ nhớ báo lỗi | Kiểm tra thông báo và quyền ghi thư mục; chỉ xem là đã lưu khi chương trình báo thành công. |

## 10. Tìm dữ liệu đã lưu

Các đường dẫn dưới đây tính từ `D:\BimBom_AI`:

| Nội dung | Thư mục |
| --- | --- |
| Tài liệu gốc, chưa tự đưa vào học | `Hoc_BimBom\Tai_Lieu` |
| Văn bản dùng cho Pretrain | `Hoc_BimBom\Du_Lieu_Huan_Luyen\Pretrain` |
| Cặp hỏi/đáp chờ duyệt | `Hoc_BimBom\Cho_Duyet` |
| Cặp hỏi/đáp đã duyệt dùng cho SFT | `Hoc_BimBom\Du_Lieu_Huan_Luyen\Chat_SFT` |
| Ghi nhớ dài hạn | `Bo_Nho_BimBom\Dai_Han` |
| Quy tắc, quy trình, ví dụ đã xác nhận | `Ky_Nang_BimBom_Hoc_Duoc` |
| Hội thoại thô và nhật ký chat | `Hoc_BimBom\Hoi_Thoai_Goc`, `Ket_Qua\Nhat_Ky_Chat` |
| Checkpoint và nhật ký train | `Ket_Qua\Checkpoint_BimBom`, `Ket_Qua\Nhat_Ky_Train` |

Các thư mục dữ liệu trống là chỗ để sử dụng về sau, không phải lỗi cài đặt. Chương trình không tự sao lưu. Không xóa checkpoint, bộ nhớ hoặc tài liệu nếu vẫn muốn tiếp tục sử dụng chúng.

Nếu cần phân tích hồ sơ theo tiêu chí hoặc dùng `chat.py --rag`/`--skills`, xem [phân tích hồ sơ và các lệnh cũ](PHAN_TICH_VA_LENH_CU.md). Những lệnh này dùng quy trình và kho kỹ năng riêng; không thay thế quy trình `/correct` → `/approve` → SFT ở trên.
