# Đọc và train nhiều file theo từng đợt

Cấu hình này dành cho máy đã kiểm tra có khoảng 24 GB RAM. BimBom chọn dữ liệu theo ngân sách mỗi đợt. File văn bản lớn hơn 16 MiB hiện được tự chia, mặc định chuẩn bị 2 phần khoảng 2 triệu ký tự mỗi nguồn. Xem [hướng dẫn tự chia dữ liệu](TU_CHIA_DU_LIEU.md). Tăng giới hạn dung lượng không làm tăng RAM; giới hạn ký tự và token vẫn cần phù hợp với máy.

## Cấu hình hiện tại

| Tham số | Giá trị | Ý nghĩa |
| --- | ---: | --- |
| `DOCUMENT_MAX_FILE_MB` | 25600 | Giới hạn file được đọc trực tiếp, theo MiB; file được tự chia thì đọc từng phần |
| `DOCUMENT_MAX_ARCHIVE_MB` | 51200 | Giới hạn tổng dung lượng giải nén của một file Office |
| `DOCUMENT_MAX_CHARACTERS` | 60000000 | Giới hạn văn bản trích xuất của một file |
| `DOCUMENT_MAX_CELLS` | 2000000 | Giới hạn số ô Excel/CSV |
| `IMPORT_MAX_TOTAL_FILE_MB` | 25600 | Ngân sách tổng dung lượng các file/phần được chọn của một đợt |
| `IMPORT_MAX_TOTAL_CHARACTERS` | 60000000 | Tổng ký tự trích xuất tối đa của một đợt |
| `TOKENIZER_CHUNK_CHARACTERS` | 32768 | Mã hóa theo đoạn để tránh một lượt xử lý khối văn bản rất lớn |
| `TRAIN_MAX_DATA_TOKENS` | 20000000 | Tổng token train và validation tối đa; vượt thì tự chọn ít file/phần hơn, giữ phần còn lại cho đợt sau |
| `DOCUMENT_READ_EXTENSIONLESS` | True | Đọc văn bản không có đuôi như `en_sents`, `vi_sents` |
| `DOCUMENT_SKIP_INVALID` | True | Khi quét thư mục, báo và bỏ qua file lỗi, tiếp tục đọc các file hợp lệ |

Không đặt trần riêng cho **số lượng file**. Chương trình ưu tiên file nhỏ trước, sau đó theo tên, để nhập được nhiều file trong ngân sách. File vượt ngân sách hoặc lỗi vẫn ở nguyên vị trí, không bị tính là đã học. File đã loại trùng hoàn toàn trong đợt không chiếm thêm ngân sách.

Định dạng đang hỗ trợ: TXT/Markdown, CSV/TSV, Word DOCX, PowerPoint PPTX, Excel XLSX/XLSM/XLS, PDF có chữ, RTF, HTML và văn bản không có đuôi. File không có đuôi phải giải mã được như văn bản; không dùng để đọc file nhị phân. DOC/PPT cũ cần chuyển đổi; PDF ảnh vẫn cần OCR.

## Cách sử dụng

1. Đặt tài liệu vào `Hoc_BimBom/Du_Lieu_Huan_Luyen/Pretrain`; thư mục con cũng được quét.
2. Chạy `run train bimbom`, chọn **3** để học tập tài liệu hiện tại từ checkpoint đã có.
3. Xem thông báo file được chọn và file tạm bỏ qua. Những file không nhập được còn được ghi trong mục ghi chú của `Du_lieu_trung.md` ở thư mục dữ liệu đã xử lý.
4. Khi phiên hoàn tất đủ điều kiện, các file/phần đã dùng được chuyển sang `Da_Hoc`. File gốc lớn đã chia luôn được giữ nguyên. Mở phiên lựa chọn **3** để nhập đợt tiếp theo. Chương trình không tự khởi chạy vô hạn các đợt sau.

Resume vẫn dùng dữ liệu trong checkpoint, không tự nhận đợt mới. Chế độ train đủ bước và các thông số batch/context/learning rate đang dùng được giữ nguyên.

## Kết quả đọc thử trước khi thêm tự chia

Thư mục hiện tại có 9 file, tổng khoảng 3,25 GB. Đã đọc thử thành công một đợt **5 file**, tổng **41.849.237 ký tự**, gồm cả `en_sents` và `vi_sents` không có đuôi.

Bốn file còn lại khi đó được giữ lại: `ViDiacritics_val.csv`, `ViDiacritics_test.csv`, `fullname.txt`, `ViDiacritics_train.csv`. Tính năng tự chia hiện xử lý các nguồn này từng phần khi chọn tạo mới/học tài liệu hiện tại, không cần nạp toàn bộ file lớn hơn 1 GB vào bộ nhớ để chia.

Tự chia CSV giữ nguyên bản ghi có ô chứa dấu phẩy hoặc xuống dòng trong dấu ngoặc kép. Các file mang tên train/validation/test của bộ dữ liệu ngoài vẫn được xử lý theo quy tắc chia hiện tại của BimBom, chưa được tự nhận diện theo tên.

Kết quả đọc thử: [báo cáo nhập nhiều file](../Ket_Qua/Danh_Gia/Bao_cao_nhap_nhieu_file_20261118.md). Chưa chạy huấn luyện trên các tài liệu này trong đợt cấu hình.

## Giới hạn còn lại

Đây là nhập theo ngân sách, chưa phải huấn luyện trực tiếp từ dữ liệu trên đĩa không giới hạn. BimBom vẫn giữ token và dữ liệu checkpoint trong bộ nhớ; lịch sử `Da_Hoc` cũng cần RAM khi đối chiếu. Khi nhiều file/phần cộng lại vượt token, chương trình tự chọn lại đợt nhỏ hơn và ghi danh sách còn chờ trong `Du_lieu_trung.md`. Nếu một file/phần riêng lẻ vẫn quá lớn, cần chia nhỏ hơn. Nếu thiếu RAM, giảm `IMPORT_MAX_TOTAL_CHARACTERS`. File không đọc được trong `Da_Hoc` được ghi rõ trong báo cáo; không thể xác định dữ liệu trùng với phần lịch sử đó.
