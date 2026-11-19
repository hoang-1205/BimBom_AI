# Train đủ số bước, không dừng vì Early Stopping

Theo cấu hình hiện tại, BimBom dùng chế độ `warn`: validation không cải thiện đủ sẽ có cảnh báo nhưng không làm phiên train dừng trước số bước đã nhập.

```python
EARLY_STOPPING_ENABLED = False
```

Chương trình vẫn đánh giá validation, lưu checkpoint định kỳ và lưu **best** riêng với **latest**. Đổi chế độ không xóa lịch sử validation, không đặt lại trọng số hoặc optimizer khi resume. Học nhiều bước hơn không bảo đảm mô hình trả lời tốt hơn; xem best và validation để đánh giá chất lượng.

## Học tiếp phiên cũ

```powershell
run train bimbom --resume --steps 3000
```

`--steps 3000` là **học thêm 3000 bước thành công** từ checkpoint gần nhất. Có thể tiếp tục ngay cả khi phiên trước đã dừng vì Early Stopping. Muốn nêu rõ chế độ trong lệnh:

```powershell
run train bimbom --resume --steps 3000 --early-stopping warn
```

Log được kiểm tra ngày 18/11/2026: phiên `20261118_182906_038876` đã hoàn thành 2100 bước trên mục tiêu 30300. Để tiếp tục đúng checkpoint đó và đạt mục tiêu cũ:

```powershell
run train bimbom --resume "D:\BimBom_AI\Ket_Qua\Checkpoint_BimBom\20261118_182906_038876\step_00002100.pt" --steps 28200
```

Khi hỏi xác nhận số bước lớn, nhập **HOC_TIEP**, hoặc nhập số nhỏ hơn nếu muốn giảm. Giới hạn hiện tại là 100000 bước học thêm mỗi lần; từ 10000 bước cần xác nhận. Chế độ warn không bỏ giới hạn số bước.

Với tài liệu mới, dùng lựa chọn **3** trong menu hoặc `--init-from best`. Không cần chọn init-from chỉ để vượt qua Early Stopping; resume giữ nguyên dữ liệu và trạng thái học dở.

## Bật lại dừng sớm cho một phiên

```powershell
run train bimbom --resume --steps 3000 --early-stopping stop
```

Cờ này ghi đè cấu hình cho phiên đang chạy. Nếu checkpoint đã chạm ngưỡng dừng sớm thì chế độ stop vẫn từ chối tiếp tục như trước. Đặt `EARLY_STOPPING_ENABLED = True` trong cấu hình nếu muốn mọi phiên mặc định dùng stop.

Lệnh trực tiếp `train.py` cũng hỗ trợ `--early-stopping warn` hoặc `stop`; lưu ý `train.py --steps` là **tổng số bước cần đạt**, khác với `run train bimbom --steps` là số bước học thêm.

## Những điều kiện vẫn có thể dừng

- Ctrl+C hoặc `run stop bimbom` yêu cầu dừng và lưu checkpoint an toàn khi có thể.
- NaN/Inf liên tiếp, trạng thái model/optimizer không hợp lệ, thiếu RAM/VRAM, hết dung lượng hoặc lỗi ghi file vẫn cần dừng để bảo vệ kết quả.
- Tắt máy hoặc mất điện phải tiếp tục từ checkpoint hoàn chỉnh gần nhất; chế độ warn không thể bảo đảm máy luôn chạy liên tục.

Không có phiên huấn luyện trên tài liệu thật nào được tự khởi chạy trong đợt điều chỉnh này. 94 kiểm thử đã đạt; gồm thử validation xấu liên tiếp nhưng vẫn đạt đủ bước, resume một checkpoint đã Early Stopping, giữ nguyên best và vẫn dừng khi gradient lỗi liên tiếp.
