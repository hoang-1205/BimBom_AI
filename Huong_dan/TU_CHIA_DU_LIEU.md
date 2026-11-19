# Tự chia dữ liệu lớn để học

BimBom tự chia file văn bản lớn thành các phần nhỏ khi chuẩn bị một phiên Pretrain mới hoặc học tài liệu hiện tại. Không cần cắt file bằng tay. File gốc được giữ nguyên, còn phần chờ học nằm trong `Hoc_BimBom/Da_Chia`.

## Cách sử dụng

1. Đặt tài liệu vào `Hoc_BimBom/Du_Lieu_Huan_Luyen/Pretrain`.
2. Chạy `run train bimbom`.
3. Chọn **3 – Học tài liệu hiện tại, giữ trọng số đã có** nếu đã có checkpoint. Chọn **2** chỉ khi muốn tạo mô hình mới từ đầu.
4. Nhập số bước học thêm. BimBom tự chuẩn bị phần dữ liệu chờ trong giới hạn cấu hình và vẫn lọc trùng trước khi học.
5. Khi phiên hoàn tất đủ điều kiện chuyển dữ liệu, các phần đã dùng chuyển sang `Da_Hoc`. Chọn **3** ở lần chạy sau để nhận các phần tiếp theo.

**Lựa chọn 1 (resume)** tiếp tục dữ liệu đã lưu trong checkpoint, không nạp phần mới. Chương trình không tự nối vô hạn các phiên huấn luyện. Số bước bạn nhập áp dụng cho đợt đang được chọn, không phải toàn bộ file gốc.

## Cấu hình trong Chinh_Che_Do.py

| Tham số | Mặc định tính năng | Ý nghĩa |
| --- | ---: | --- |
| `AUTO_SPLIT_LARGE_FILES` | `True` | Bật tự chia khi chuẩn bị Pretrain |
| `AUTO_SPLIT_TRIGGER_MB` | `16` | Chia file lớn hơn 16 MiB |
| `AUTO_SPLIT_PART_CHARACTERS` | `2000000` | Mục tiêu khoảng 2 triệu ký tự mỗi phần |
| `AUTO_SPLIT_PENDING_PARTS` | `2` | Tạo tối đa 2 phần chờ mỗi file nguồn trong một lượt |
| `AUTO_SPLIT_MAX_RECORD_CHARACTERS` | `8000000` | Giới hạn một bản ghi CSV để tránh đọc vô hạn khi dấu ngoặc kép lỗi |
| `AUTO_SPLIT_CSV_HAS_HEADER` | `True` | CSV/TSV có dòng tiêu đề; lặp tiêu đề trong mỗi phần |

CSV không có tiêu đề: đặt `AUTO_SPLIT_CSV_HAS_HEADER = False` **trước khi tạo hàng đợi lần đầu**. Cài đặt này dùng chung cho các CSV mới được chia. Hàng đợi đã tạo giữ thông tin tiêu đề và mã hóa đã lưu; đổi cấu hình không diễn giải lại phần đã đọc.

Các ngưỡng tổng ký tự, token và dung lượng nhập vẫn áp dụng. Nếu tổng token vượt `TRAIN_MAX_DATA_TOKENS`, BimBom tự chọn ít file/phần hơn, ưu tiên phần ít token, chia lại train/validation và mã hóa lại. Màn hình hiển thị số token thực tế và số phần còn chờ. File/phần chưa được chọn được ghi trong `Du_lieu_trung.md` với lý do ngân sách token, không được đánh dấu đã học hoặc chuyển sang `Da_Hoc`.

Nếu ngay cả một file/phần riêng lẻ cũng không vừa giới hạn, cần chia phần đó nhỏ hơn; chương trình không cắt bỏ đuôi dữ liệu rồi coi cả file là đã học. Hai tập train/validation vẫn phải đủ nội dung độc lập để đánh giá. Nếu thiếu RAM, giảm `IMPORT_MAX_TOTAL_CHARACTERS`, số phần chờ hoặc kích thước phần. Đây là chuẩn bị dữ liệu theo đợt; bước train vẫn giữ token trong bộ nhớ, không phải đọc không giới hạn trực tiếp từ đĩa.

## Định dạng và cách chia

- Tự chia: CSV, TSV, TXT, MD/Markdown, TEXT, LOG và văn bản không có đuôi khi được phép đọc.
- CSV/TSV: giữ nguyên bản ghi, kể cả ô chứa dấu phân cách hoặc xuống dòng trong ngoặc kép. Một bản ghi lớn có thể làm phần vượt mục tiêu 2 triệu ký tự; bản ghi vượt giới hạn an toàn sẽ báo lỗi.
- Văn bản: ưu tiên đọc theo dòng. Dòng quá dài có thể chia ở ranh giới ký tự; không làm mất ký tự giữa các phần.
- UTF-8, UTF-16/32 có BOM được nhận diện; mã hóa khác dùng `DOCUMENT_TEXT_ENCODING`.
- Word, PowerPoint, Excel, PDF và HTML vẫn dùng bộ đọc hiện có; tính năng này chưa tự chia các định dạng đó.

Việc chia trước mắt giữ giới hạn kích thước và ranh giới bản ghi, chưa chia theo ý nghĩa/chủ đề. Tên file chứa train/validation/test chưa được dùng để tự gán vai trò; BimBom vẫn dùng quy tắc chia tập hiện có.

## Tiến độ, dữ liệu trùng và file gốc

Mỗi phiên bản nguồn có một thư mục riêng trong `Hoc_BimBom/Da_Chia`, gồm các phần và `manifest.json` ghi vị trí đọc. Mở lại chương trình sẽ dùng phần còn chờ. Chỉ đọc tiếp khi không còn phần chờ của nguồn đó; không chia toàn bộ file lớn ngay từ đầu.

Phần trùng hoàn toàn với lịch sử `Da_Hoc` được ghi vào `Du_lieu_trung.md` của đợt chuẩn bị, giữ tại `Da_Chia` và đánh dấu bỏ qua; không tính là vừa huấn luyện. Nếu cả đợt chỉ chứa dữ liệu trùng, chương trình báo chưa có nội dung mới. Chọn **3** lần nữa để lấy phần tiếp theo nếu nguồn còn dữ liệu. Phần trùng với phần khác trong cùng đợt vẫn được giữ chờ, rồi đối chiếu lịch sử ở lần nhập sau.

File gốc lớn luôn ở nguyên thư mục nguồn, kể cả khi đã xử lý hết. Dữ liệu được dùng không có nghĩa là mô hình đã nắm vững kiến thức. File nhỏ vẫn chuyển sang `Da_Hoc` theo quy tắc hiện có.

Không tự xóa hoặc sửa các phần, `manifest.json` hay các phần đã chuyển sang `Da_Hoc`: chương trình kiểm tra dấu vết và báo lỗi nếu thiếu hoặc thay đổi. Khi nguồn đổi kích thước hoặc thời gian sửa, chương trình tạo hàng đợi phiên bản mới, giữ phiên bản cũ để đối chiếu. Tránh sửa nguồn khi đang chia hoặc train.

Nếu dừng giữa chừng, phần chưa ghi nhận hoàn chỉnh không làm tăng vị trí đọc đã lưu. Phần chưa được dùng thành công không chuyển sang `Da_Hoc`. Lệnh xem trạng thái không tạo thêm phần mới.
