# Giới thiệu BimBom AI

[Cách sử dụng](CACH_SU_DUNG.md) | [Phân tích hồ sơ và lệnh cũ](PHAN_TICH_VA_LENH_CU.md)

## Bắt đầu đọc từ đâu?

- Mở/tắt AI, chat, dạy bộ nhớ, huấn luyện và xử lý lỗi: [CACH_SU_DUNG.md](CACH_SU_DUNG.md).
- Chỉnh chế độ chat, CPU/GPU, mức tải và thông số huấn luyện: [Huong_dan_che_do_va_cau_hinh.md](Huong_dan_che_do_va_cau_hinh.md).
- Phân tích hồ sơ theo tiêu chí, xuất báo cáo cho giáo viên và các lệnh tương thích cũ: [PHAN_TICH_VA_LENH_CU.md](PHAN_TICH_VA_LENH_CU.md).

Hướng dẫn sử dụng hiện tại nằm trong thư mục này. Tệp `HUONG_DAN_BIMBOM_AI.md` ở gốc dự án chỉ dẫn đến đây để tránh có nhiều bản hướng dẫn đầy đủ bị lệch nhau.

## BimBom làm được gì?

| Chức năng | Cách hoạt động |
| --- | --- |
| Chat | Sinh câu trả lời bằng mô hình cục bộ khi có checkpoint; thông báo rõ khi chưa có mô hình đã học. |
| Bộ nhớ | Lưu, xem, sửa, xóa kiến thức do người dùng xác nhận; đọc lại ghi nhớ liên quan ở phiên sau. |
| Quy tắc và quy trình | Lưu bằng `/rule` và `/workflow`, đưa nội dung liên quan vào ngữ cảnh chat. |
| Duyệt dữ liệu chat | `/correct` tạo bản nháp; `/approve` xác nhận để xuất cặp hỏi/đáp cho huấn luyện. |
| Pretrain | Học ngôn ngữ từ văn bản đã chuẩn bị, khởi tạo mô hình và tokenizer từ đầu. |
| SFT | Học cách trả lời từ cặp hỏi/đáp đã duyệt, dùng trọng số và tokenizer của checkpoint nền. |
| Học tiếp | Khôi phục checkpoint hợp lệ hoặc giữ trọng số để học tập dữ liệu mới. |
| Tắt phiên | `run stop bimbom` hoặc `run tat bimbom`; train lưu checkpoint trước khi dừng. |
| Phân tích hồ sơ | Chức năng riêng `phan_tich.py`, đối chiếu với tiêu chí viết sẵn, không cần mô hình đã huấn luyện. |

## Phân biệt ba việc

**Lưu bộ nhớ:** `/remember` ghi thông tin lên đĩa sau xác nhận. Thông tin có thể được đưa vào ngữ cảnh ở lần chat sau, nhưng trọng số mô hình không thay đổi.

**Duyệt ví dụ:** `/correct` và `/approve` chuẩn bị dữ liệu học. Chỉ việc duyệt chưa khiến mô hình học ví dụ đó.

**Huấn luyện:** `run train bimbom` mới cập nhật trọng số. Tiếp tục cùng dữ liệu dùng checkpoint; học dữ liệu mới dùng `--init-from`. Chất lượng phụ thuộc dữ liệu, kiến trúc và quá trình đánh giá; mô hình nhỏ chưa chắc trò chuyện tốt.

## Trạng thái và cách vận hành

Dự án đã được đặt lại và nâng cấp ngày 18/11/2026, không tạo sao lưu. Tại lần bàn giao sau dọn dẹp, AI chính chưa có dữ liệu học hoặc checkpoint. Trạng thái có thể thay đổi khi bạn sử dụng; chạy `run status bimbom` để xem thông tin hiện tại.

Dùng duy nhất môi trường Python tại `D:\BimBom_AI\Model_BimBomAI\.venv`. Chat và train chạy lần lượt. Trong cửa sổ chat, `/tat`, `/stop`, `/exit` và `/thoat` đều thoát phiên. Lệnh tắt BimBom không tắt máy tính và không xóa bộ nhớ.

## Phân tích hồ sơ và báo cáo

`phan_tich.py` dùng tiêu chí nghề viết sẵn, không phải mô hình đã học cách đánh giá con người. Điểm cho biết mức đối chiếu theo dữ liệu nhập, không phải xác suất thành công hoặc quyết định tuyển dụng. Tiêu chí mẫu cần được điều chỉnh và kiểm tra với minh chứng thực tế.

Phân tích hồ sơ và `chat.py` cũ có thể xuất Markdown để giáo viên xem xét. `run chat bimbom` lưu hội thoại theo cấu hình `LOG_CHAT` và dùng quy trình duyệt riêng. Ghi nhận xét vào báo cáo không tự cập nhật trọng số hoặc tự đưa dữ liệu vào huấn luyện.
