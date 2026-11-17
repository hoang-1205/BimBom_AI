# BimBom AI

Đã nâng cấp theo kế hoạch ngày 18/11/2026, **không tạo bản sao lưu**. Mô hình chính vẫn chưa được huấn luyện; dữ liệu và checkpoint thử nghiệm không được đưa vào dự án.

## Bắt đầu

```powershell
cd D:\BimBom_AI
.\run.cmd status bimbom
.\run.cmd chat bimbom
.\run.cmd train bimbom
.\run.cmd stop bimbom
```

Lệnh train hỏi số bước **muốn học thêm**, tự chọn checkpoint hợp lệ và tương thích. Nếu chưa có checkpoint, cần thêm TXT/MD đã kiểm tra vào `Hoc_BimBom\Du_Lieu_Huan_Luyen\Pretrain`. Chat khi chưa có checkpoint chỉ quản lý/trích dẫn bộ nhớ; không giả lập câu trả lời của mô hình.

Đọc [hướng dẫn sử dụng](Huong_dan_va_cach_su_dung/CACH_SU_DUNG.md) để dùng `/remember`, `/correct`, duyệt dữ liệu SFT, tiếp tục huấn luyện và cấu hình chế độ.

`run stop bimbom` (hoặc `run tat bimbom`) tắt phiên đang chạy. Chat thoát kể cả khi đang chờ nhập; train hoàn tất bước hiện tại và lưu checkpoint rồi dừng. Trong cửa sổ chat có thể gõ `/stop`, `/tat` hoặc `/exit`.

## Các phần chính

- `Run_BimBom.py`, `run.cmd`: bộ điều khiển chat/train/status/stop, dùng duy nhất `Model_BimBomAI\.venv`.
- `Chat_BimBom.py`: hội thoại, bộ nhớ xác nhận, hàng chờ duyệt; không tự huấn luyện khi chat.
- `Chinh_Che_Do.py`: thiết bị, kiến trúc, chế độ chat và giới hạn tài nguyên.
- `train.py`: Pretrain/SFT, lưu và khôi phục model, optimizer, RNG, scaler, tokenizer, dữ liệu.
- `Model_BimBomAI\Ma_Nguon`: kiểm tra checkpoint, bộ nhớ, suy luận, dữ liệu và khóa phiên.
- `Hoc_BimBom`: tài liệu gốc, hội thoại thô, hàng chờ, dữ liệu Pretrain và Chat_SFT tách biệt.
- `Bo_Nho_BimBom`, `Ky_Nang_BimBom_Hoc_Duoc`: ghi nhớ và ví dụ đã xác nhận.
- `Ket_Qua`: checkpoint, dữ liệu đã xử lý, nhật ký và đánh giá.

Các chức năng phân tích hồ sơ và lệnh `chat.py` cũ vẫn được giữ. Dữ liệu mẫu trong `Du_Lieu\Phan_Tich` không tự trở thành dữ liệu huấn luyện. Lệnh `--include-approved` cũ nay báo hướng dẫn chuyển sang SFT để tránh trộn sai dữ liệu.

