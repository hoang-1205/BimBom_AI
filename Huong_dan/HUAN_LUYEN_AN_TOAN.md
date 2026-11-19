# Huấn luyện an toàn: NaN/Inf, Early Stopping và checkpoint

[Cách sử dụng](CACH_SU_DUNG.md) | [Chế độ và cấu hình](Huong_dan_che_do_va_cau_hinh.md)

Bản cập nhật ngày 18/11/2026 giữ nguyên cấu trúc thư mục hiện tại, tài liệu học và checkpoint/kết quả cũ. Chỉ sử dụng `Model_BimBomAI\.venv`. Không có lần huấn luyện chính nào được chạy trong đợt sửa; các lượt kiểm thử dùng dữ liệu tạm và tự dọn sau khi hoàn thành.

## 1. Chọn đúng cách học

```powershell
cd D:\BimBom_AI
.\run.cmd train bimbom
```

Menu gồm:

1. **Tiếp tục checkpoint gần nhất tương thích:** giữ trọng số, tokenizer, optimizer, scaler, RNG, dữ liệu và số bước đã học. Không có checkpoint phù hợp thì dừng; không tự chuyển sang tạo mô hình mới.
2. **Tạo mô hình mới từ đầu:** khởi tạo tokenizer và trọng số ngẫu nhiên cho Pretrain. Kết quả lưu vào thư mục lần chạy mới, không xóa các lần trước.
3. **Học dữ liệu mới từ trọng số cũ:** nhập đường dẫn checkpoint nền hoặc `best`. Giữ trọng số/tokenizer, tạo optimizer mới, đọc tập dữ liệu hiện tại và bắt đầu đếm bước từ 0 cho giai đoạn mới.

Có thể chọn rõ qua lệnh, không qua menu:

```powershell
# Học tiếp bản tương thích gần nhất, thêm 100 cập nhật thành công:
.\run.cmd train bimbom --resume --steps 100

# Học tiếp checkpoint cụ thể; --checkpoint là tên tương đương --resume:
.\run.cmd train bimbom --resume "DUONG_DAN_CHECKPOINT.pt" --steps 100

# Chủ động tạo mô hình mới:
.\run.cmd train bimbom --new --steps 100

# Giữ trọng số để học văn bản mới; best được kiểm tra trên cùng dữ liệu/tokenizer:
.\run.cmd train bimbom --init-from best --stage pretrain --steps 100

# Học cặp hỏi–đáp đã duyệt:
.\run.cmd train bimbom --init-from "DUONG_DAN_CHECKPOINT.pt" --stage sft --steps 100
```

Thay đường dẫn mẫu bằng file `.pt` thật. `--resume` không nạp tài liệu mới; bộ chạy sẽ báo các file thêm/xóa/thay đổi so với manifest cũ. `--init-from` đọc lại toàn bộ tập dữ liệu được chọn, không chỉ riêng những file mới. Tài liệu trùng nội dung sau chuẩn hóa Unicode và khoảng trắng chỉ được đọc một lần; file gốc vẫn giữ nguyên.

Lệnh trực tiếp `train.py --steps` vẫn là **tổng bước thành công cần đạt**. `run train bimbom --steps` là **số bước thành công học thêm**.

## 2. Gradient NaN/Inf và overflow

Mỗi lần thử cập nhật được đếm vào `attempts`. Chỉ khi optimizer thực sự cập nhật và model/optimizer vẫn hữu hạn thì mới tăng `step`.

- Loss NaN/Inf: bỏ lượt thử, xóa gradient đang tích lũy và giảm scale khi dùng FP16.
- Gradient NaN/Inf: phát hiện sau `unscale_`, trước khi cắt gradient. Với FP16, GradScaler bỏ optimizer update và cập nhật scale theo trạng thái overflow.
- Gradient hữu hạn nhưng quá lớn: tính norm bằng float64 trước khi cắt để tránh overflow của phép cộng bình phương float32.
- Năm lần lỗi liên tiếp theo mặc định: dừng an toàn, lưu trạng thái còn hợp lệ. Một bước thành công đặt lại bộ đếm lỗi liên tiếp.
- Trọng số hoặc optimizer thành NaN/Inf sau cập nhật: dừng, không ghi trạng thái đó; báo checkpoint hợp lệ trước đó để phục hồi.

Log có `skipped_steps`, `consecutive_nonfinite`, `overflow_count`, `invalid_loss_count` và `grad_norm`. Norm không hợp lệ được ghi `null` kèm lý do trong sự kiện, không ghi NaN/Infinity vào JSON.

Checkpoint cũ có thể đã tính lượt bỏ qua là bước thành công. Bộ chạy kiểm tra bộ đếm Adam để xác định số bước thực tế, in cảnh báo nếu khác số ghi trên checkpoint, và không sửa file cũ.

## 3. Early Stopping và overfitting

```python
EVAL_EVERY_STEPS = 100
EARLY_STOPPING_ENABLED = False  # mặc định: cảnh báo, tiếp tục đủ bước
EARLY_STOPPING_PATIENCE = 4
EARLY_STOPPING_MIN_DELTA = 0.01
```

Đánh giá ở bước đầu, định kỳ và trước khi kết thúc/lưu theo yêu cầu. Khi validation loss không cải thiện đủ 0,01 sau 4 lần đánh giá liên tiếp, chương trình dừng. Các cải thiện nhỏ được so với mốc cải thiện đáng kể gần nhất; mọi validation loss thấp hơn vẫn được ghi nhận làm best.

Resume giữ lịch sử chờ và mốc validation tốt nhất trên cùng dữ liệu/tokenizer. Đánh giá lại cùng một bước khi resume không làm tăng thêm bộ đếm. Mặc định hiện tại `warn` chỉ cảnh báo và tiếp tục đủ bước, kể cả checkpoint trước đã Early Stopping. Với `--early-stopping stop` hoặc cấu hình `EARLY_STOPPING_ENABLED = True`, bộ chạy mới áp dụng dừng sớm như trước. Không xóa lịch sử hoặc trọng số khi đổi chế độ. Xem [train đủ số bước](TRAIN_DU_SO_BUOC.md).

Thông báo overfitting xuất hiện khi validation kém mốc tốt nhất trong lúc có khoảng cách lớn với train loss hoặc train loss giảm còn validation tăng. Đây là tín hiệu cần kiểm tra, không phải bằng chứng rằng chỉ đổi batch/LR sẽ khắc phục vấn đề dữ liệu.

## 4. Best khác latest

- `latest.json`: trạng thái gần nhất đã ghi hoàn chỉnh, dùng để tiếp tục chính xác.
- `best.json`: checkpoint có validation loss thấp nhất đã xác minh trên cùng dữ liệu, tokenizer, kiến trúc và giai đoạn. Khi resume, có thể trỏ về một file ở lần chạy trước.
- Chat mặc định ưu tiên best của cùng tập dữ liệu/tokenizer với bản hợp lệ gần nhất; chưa xác định được best thì thông báo rõ trước khi dùng bản gần nhất.
- Không so sánh trực tiếp loss của các tập dữ liệu hoặc tokenizer khác nhau để chọn best toàn cục.
- Các checkpoint có tên riêng; không ghi đè checkpoint cũ hoặc best bằng trạng thái kém hơn. File được ghi tạm, flush/fsync rồi thay thế an toàn. Các con trỏ JSON cũng ghi nguyên tử.

Dùng `run status bimbom` để xem `checkpoint` (latest), `step` (bước thực tế), `legacy_reported_step`, `best_checkpoint`, `best_validation_loss` và `dataset_changes`.

## 5. Giới hạn số bước và dừng phiên

```python
TRAIN_WARN_ADDITIONAL_STEPS = 10000
TRAIN_MAX_ADDITIONAL_STEPS = 100000
MAX_CONSECUTIVE_NONFINITE = 5
```

Từ 10.000 bước bổ sung, phải nhập `HOC_TIEP`. Khi chạy tự động, cờ `--confirm-large-run` thể hiện xác nhận này; cờ không vượt được giới hạn cứng 100.000 bước bổ sung. Yêu cầu 10.000.000 bước sẽ bị từ chối trước khi train.

Bộ chạy hiển thị số bước đã hoàn thành, số học thêm và tổng mục tiêu. Nếu có tốc độ ở lần resume trước thì in ước tính ban đầu; trong lúc học, mỗi log đánh giá cập nhật `steps_per_second` và `estimated_remaining_seconds`. Ước tính có thể thay đổi và chưa tính việc dừng sớm.

`run stop bimbom` hoặc Ctrl+C một lần yêu cầu hoàn tất bước hiện tại rồi lưu checkpoint hợp lệ. Khi đang chuẩn bị dữ liệu cần chờ khâu đó hoàn tất. Ctrl+C lần thứ hai buộc dừng; khi đó chỉ dùng checkpoint đã ghi hoàn chỉnh. Tắt đột ngột hoặc lỗi phần cứng vẫn có thể làm mất phần chưa lưu.

## 6. Một hoặc nhiều tài liệu

- Không có tài liệu: báo thiếu dữ liệu.
- Một tài liệu đủ dài: chia phần đầu khoảng 85% cho train và phần còn lại cho validation, ưu tiên ranh giới dòng để không cắt đôi đoạn lặp. Văn bản một dòng dùng ranh giới từ. Manifest ghi vị trí hai phần trong nội dung nguồn trước khi lọc trùng.
- Nhiều tài liệu khác nhau: ưu tiên chia theo tài liệu, khoảng 15% số tài liệu cho validation, ít nhất một tài liệu.
- Mỗi phần phải có ít nhất `MIN_TOKENS_PER_SPLIT = 32` token nội dung. Quá ngắn sẽ bị từ chối, không tạo validation loss giả. Ngưỡng này không bảo đảm tập đánh giá đủ đa dạng.
- Các dòng giống nhau sau chuẩn hóa khoảng trắng và dài ít nhất 80 ký tự xuất hiện ở cả hai tập được loại khỏi **bản train trong bộ nhớ**; validation và file nguồn được giữ nguyên. Chương trình kiểm tra lại để bảo đảm không còn các dòng trùng theo tiêu chí này. Nếu phần còn lại không đủ token độc lập, chương trình vẫn dừng, không bỏ kiểm tra hoặc tạo validation giả. Cách này không phát hiện mọi biến thể gần giống, trùng nghĩa hoặc dòng ngắn.
- Manifest lưu `overlap_cleanup` (số đoạn trùng, số dòng/ký tự đã lọc, nguồn liên quan) và hash của nội dung sau lọc. `source_documents` vẫn mô tả tài liệu gốc để theo dõi thay đổi và chuyển đúng file sang `Da_Hoc`. Resume dùng dữ liệu đã mã hóa trong checkpoint, không tự áp dụng lại bộ lọc cho checkpoint cũ.
- File trùng hoàn toàn, dòng dài lặp trong train và (khi init-from) nội dung đã có trong `Da_Hoc` cũng được tạm bỏ qua. Mỗi lần chuẩn bị có `Du_lieu_trung.md`, kể cả khi dừng do không còn đủ nội dung mới. Xem [quy tắc chi tiết](DU_LIEU_TRUNG.md).

Kiểm tra thực tế ngày 18/11/2026: ba file Pretrain chỉ có **hai nội dung khác nhau**. Hai file `hoc_tra_loi_tieng_viet.md` và `hoc_tra_loi_tieng_viet2.md` trùng nội dung sau chuẩn hóa. Với seed 42, tập train chỉ lấy file trả lời tiếng Việt; validation lấy file phân tích. Vì vậy cần bổ sung nhiều tài liệu độc lập và đa dạng hơn cho cả hai tập. Không nhân đôi cùng nội dung để tăng số file. Báo cáo chi tiết tại `Ket_Qua/Danh_Gia/kiem_tra_du_lieu_20261118.json`; không có file nguồn nào bị xóa hoặc sửa.

## 7. Cấu hình mới và checkpoint cũ

Cấu hình cho lần mới/`--init-from`: batch 2, accumulation 16, LR 0,0001, context 256, FP16 trên CUDA, checkpoint mỗi 200 bước. Giữ batch hiện tại để ưu tiên ổn định; chưa tự tăng lên 4. Đây không phải khẳng định đã tối ưu tốc độ hoặc chữa được overfitting.

Checkpoint cũ thực tế lưu batch 3, accumulation 16, LR 0,0003. Resume giữ những thông số đó. Muốn áp dụng LR mới mà vẫn giữ trọng số, dùng `--init-from`, hiểu rằng optimizer và số bước của giai đoạn mới được đặt lại. Các giới hạn an toàn/Early Stopping được đọc từ cấu hình hiện tại cả khi resume.

## 8. Kiểm thử và kết quả

Chạy bằng đúng môi trường đang có, sau khi dừng phiên AI khác:

```powershell
cd D:\BimBom_AI
.\Model_BimBomAI\.venv\Scripts\python.exe -B Ket_Qua\Danh_Gia\kiem_tra_nang_cap_20261118.py
```

Kịch bản kiểm tra cú pháp, CUDA, một tài liệu, dữ liệu trùng, dừng/resume, GradScaler với NaN/Inf, norm lớn, bộ đếm bước bỏ qua, Early Stopping/best, từ chối resume thiếu checkpoint, giới hạn bước, từ chối lưu trọng số lỗi và Ctrl+C. Dữ liệu thử được tạo ở vị trí riêng rồi tự dọn; không dùng để huấn luyện mô hình chính và không tái tạo thư mục tests ở gốc.

Bản kiểm kê trước sửa chỉ ghi đường dẫn, kích thước và thời gian sửa tệp để đối chiếu, không sao chép dữ liệu. Các kết quả kiểm thử và kiểm kê nằm trong `Ket_Qua/Danh_Gia`.
