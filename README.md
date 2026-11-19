# BimBom AI

Đã nâng cấp bảo vệ huấn luyện ngày 18/11/2026: Early Stopping, xử lý NaN/Inf, giới hạn số bước và chọn rõ cách học. Giữ nguyên checkpoint, tài liệu và kết quả huấn luyện cũ; kiểm thử chỉ dùng dữ liệu tạm.

## Bắt đầu

Đã rà soát train/chat, xử lý file lỗi và cải thiện lấy mẫu dữ liệu; xem [báo cáo kiểm tra ngày 18/11/2026](Huong_dan/BAO_CAO_RA_SOAT_20261118.md).

```powershell
cd D:\BimBom_AI
.\run.cmd status bimbom
.\run.cmd chat bimbom
.\run.cmd train bimbom
.\run.cmd stop bimbom
```

Lệnh train có menu: **1. Resume**, **2. Tạo mô hình mới**, **3. Học dữ liệu mới từ trọng số cũ**. Chọn resume mà không có checkpoint phù hợp sẽ dừng, không tự tạo trọng số mới. Số bước nhập là optimizer steps thành công muốn học thêm; các lần NaN/Inf bị bỏ qua không được tính.

Đọc [hướng dẫn sử dụng](Huong_dan/CACH_SU_DUNG.md) và [hướng dẫn bảo vệ huấn luyện](Huong_dan/HUAN_LUYEN_AN_TOAN.md). Lệnh nhanh: `run train bimbom --resume --steps 100` để học tiếp, `--new` để tạo mới, hoặc `--init-from "CHECKPOINT.pt"` để đọc dữ liệu mới. Chat ưu tiên best trên cùng tập dữ liệu/tokenizer; latest không đồng nghĩa best.

Luồng nhanh để học tài liệu mới: `run train bimbom` → **3** → **Enter** chọn best → **Enter** học thêm 200 bước. Mặc định chỉ cảnh báo validation và học đủ bước, không dừng vì Early Stopping; best vẫn được giữ riêng. [Quy trình train rút gọn](Huong_dan/TRAIN_NHANH.md) | [Train đủ số bước và bật lại dừng sớm](Huong_dan/TRAIN_DU_SO_BUOC.md).

`run stop bimbom` (hoặc `run tat bimbom`) tắt phiên đang chạy. Chat thoát kể cả khi đang chờ nhập; train hoàn tất bước hiện tại và lưu checkpoint rồi dừng. Trong cửa sổ chat có thể gõ `/stop`, `/tat` hoặc `/exit`.

## Các phần chính

- `Run_BimBom.py`, `run.cmd`: bộ điều khiển chat/train/status/stop, dùng duy nhất `Model_BimBomAI\.venv`.
- `Chat_BimBom.py`: hội thoại, bộ nhớ xác nhận, hàng chờ duyệt; không tự huấn luyện khi chat.
- `Chinh_Che_Do.py`: thiết bị, kiến trúc, chế độ chat và giới hạn tài nguyên.
- `train.py`: Pretrain/SFT, lưu và khôi phục model, optimizer, RNG, scaler, tokenizer, dữ liệu.
- `Model_BimBomAI\Ma_Nguon`: kiểm tra checkpoint, bộ nhớ, suy luận, dữ liệu và khóa phiên.
- `Hoc_BimBom`: tài liệu gốc, hội thoại thô, hàng chờ, dữ liệu Pretrain và Chat_SFT tách biệt.
- `Da_Hoc`: tự nhận các file của tập dữ liệu sau khi phiên học hoàn tất và lưu checkpoint hợp lệ. [Điều kiện và cách dùng](Huong_dan/DA_HOC.md).
- `Bo_Nho_BimBom`, `Ky_Nang_BimBom_Hoc_Duoc`: ghi nhớ và ví dụ đã xác nhận.
- `Ket_Qua`: checkpoint, dữ liệu đã xử lý, nhật ký và đánh giá.

Các chức năng phân tích hồ sơ và lệnh `chat.py` cũ vẫn được giữ. Dữ liệu mẫu trong `Du_Lieu\Phan_Tich` không tự trở thành dữ liệu huấn luyện. Lệnh `--include-approved` cũ nay báo hướng dẫn chuyển sang SFT để tránh trộn sai dữ liệu.


## Đọc tài liệu

Đã cấu hình nhập nhiều file theo ngân sách bộ nhớ, ưu tiên file nhỏ và nhận văn bản không có đuôi. Xem [train nhiều file theo từng đợt](Huong_dan/TRAIN_NHIEU_FILE.md).

Đã hỗ trợ Word DOCX, PowerPoint PPTX, Excel XLSX/XLS/XLSM, CSV/TSV, PDF có chữ, RTF, HTML và văn bản. Dùng `run read bimbom "DUONG_DAN_FILE"` để xem trước; đặt tài liệu đã kiểm tra vào Pretrain nếu muốn huấn luyện. [Hướng dẫn đọc tài liệu](Huong_dan/DOC_TAI_LIEU.md).
