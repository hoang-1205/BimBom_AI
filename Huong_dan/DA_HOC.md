# Tự chuyển tài liệu sang Da_Hoc sau khi học

Thư mục lưu tài liệu đã dùng là `D:\BimBom_AI\Da_Hoc`, nằm ngang cấp với `Hoc_BimBom`. Chức năng tự hoạt động trong các lần huấn luyện thông thường tiếp theo, không cần bật thêm. Không tự gom hoặc chuyển các tài liệu từ những lần huấn luyện đã kết thúc trước khi có chức năng này.

## Khi nào file được chuyển?

- Phiên đạt số bước yêu cầu, hoặc Early Stopping kết thúc phiên sau khi đã có ít nhất một bước cập nhật thành công trong phiên đó.
- Checkpoint cuối đã lưu và vượt qua kiểm tra hợp lệ.
- File có trong danh sách dữ liệu thực sự dùng cho phiên, nằm trong `Hoc_BimBom`, và nội dung còn khớp với lúc chuẩn bị học.

Toàn bộ tài liệu nguồn của tập dữ liệu được lưu cùng nhau, gồm cả phần train và validation. Tên `Da_Hoc` có nghĩa là **đã dùng trong một phiên huấn luyện hoàn tất**, không bảo đảm mô hình đã thuộc mọi nội dung hay đạt chất lượng tốt.

Ví dụ:

```text
Hoc_BimBom/Du_Lieu_Huan_Luyen/Pretrain/archive/train.csv
    → Da_Hoc/TEN_LAN_HUAN_LUYEN/Du_Lieu_Huan_Luyen/Pretrain/archive/train.csv
```

File được di chuyển nguyên bản, giữ tên và cấu trúc thư mục con. Mỗi lần huấn luyện có thư mục riêng; không ghi đè file đã lưu. Thư mục nguồn rỗng được giữ nguyên để tiếp tục nhận tài liệu mới. Không tạo bản sao lưu thứ hai.

## Những trường hợp giữ nguyên file

- Chọn thoát, lỗi huấn luyện, NaN/Inf khiến dừng, Ctrl+C hoặc `run stop bimbom`.
- Resume bị Early Stopping ngay và chưa có thêm bước cập nhật thành công.
- File mới thêm trong lúc học hoặc chưa có trong danh sách dữ liệu của checkpoint.
- File đã sửa, không còn khớp dữ liệu đã học, bị khóa hoặc không có quyền di chuyển.
- File trùng đã bị loại khỏi tập dữ liệu, file không hỗ trợ hoặc tài liệu chỉ lưu trong `Tai_Lieu`, `Hoi_Thoai_Goc`, `Cho_Duyet` mà chưa được chọn vào tập học.
- File ngoài `Hoc_BimBom`, file qua liên kết/junction, phiên `--smoke`, hoặc phiên dùng `--output-root` khác thư mục `Ket_Qua` mặc định.

Pretrain và các cặp JSON đã duyệt của Chat_SFT đều được hỗ trợ. Bộ nhớ và bản ví dụ đã xác nhận trong `Ky_Nang_BimBom_Hoc_Duoc` không bị di chuyển.

## Học tiếp và đọc lại tài liệu

Resume vẫn chạy được sau khi file đã chuyển vì checkpoint chứa dữ liệu đã mã hóa. Resume chỉ xét các nguồn trong checkpoint, không chuyển các file mới chưa học. Nếu thông báo dữ liệu hiện tại có file bị thiếu sau khi lưu vào `Da_Hoc`, đó là do file đã được chuyển; dữ liệu trong checkpoint vẫn còn.

`Da_Hoc` không tự được đưa vào tập học mới. Với Pretrain `--init-from`, chương trình đọc `Da_Hoc` để bỏ qua nội dung đã dùng; chép nguyên file cũ trở lại Pretrain sẽ khiến file bị bỏ qua nếu vẫn khớp lịch sử. Khi chủ động tạo mô hình mới từ đầu, có thể đưa file cần dùng trở lại Pretrain và chương trình không lọc theo lịch sử. Lệnh `run read bimbom "DUONG_DAN_FILE"` vẫn đọc được một file cụ thể trong `Da_Hoc`. Xem [cơ chế lọc và báo cáo dữ liệu trùng](DU_LIEU_TRUNG.md).

## Nhật ký di chuyển

Trong thư mục checkpoint của phiên có `archived_sources.json`, ghi nguồn, đích, mã kiểm tra nội dung, file đã chuyển và lý do bỏ qua. Kế hoạch cho từng file được ghi trước khi di chuyển. Nếu máy bị tắt giữa chừng, trường `pending` giúp đối chiếu file ở nguồn/đích; chương trình không tự ghi đè hoặc xóa để thử lại.

Nếu việc chuyển file gặp lỗi sau khi học xong, checkpoint đã lưu vẫn được giữ. Xem thông báo cuối phiên và nhật ký để biết file nào còn ở vị trí cũ.
