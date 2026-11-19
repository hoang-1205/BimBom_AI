# Đọc Word, PowerPoint, Excel, CSV và tài liệu văn bản

[Cách sử dụng](CACH_SU_DUNG.md) | [Chế độ và cấu hình](Huong_dan_che_do_va_cau_hinh.md)

BimBom có bộ trích xuất văn bản dùng chung cho Pretrain và tra cứu tài liệu (`chat.py --rag`). Không cần mở Word/PowerPoint/Excel để đọc các định dạng được hỗ trợ. Đọc file chỉ lấy nội dung; không tự huấn luyện hoặc cập nhật trọng số.

## 1. Các định dạng hỗ trợ

| Nhóm | Đuôi file | Nội dung được đọc |
| --- | --- | --- |
| Văn bản | `.txt`, `.md`, `.markdown`, `.text`, `.log` | Văn bản thuần. |
| Word | `.docx` | Đoạn văn và bảng trong thân tài liệu, gồm bảng lồng nhau. |
| PowerPoint | `.pptx` | Chữ trong slide, nhóm đối tượng, bảng và ghi chú người trình bày. |
| Excel | `.xlsx`, `.xlsm` | Tất cả trang tính, gồm trang ẩn; dữ liệu ô và kết quả công thức đã lưu. Không chạy macro. |
| Excel cũ | `.xls` | Giá trị ô đã lưu; không tính lại công thức hoặc chạy macro. |
| Bảng văn bản | `.csv`, `.tsv` | Hàng/cột; CSV nhận dấu phẩy, chấm phẩy, tab hoặc dấu gạch đứng. |
| PDF | `.pdf` | Văn bản có lớp chữ. PDF chỉ có ảnh cần OCR trước. |
| Rich Text | `.rtf` | Văn bản từ tài liệu RTF. |
| HTML cục bộ | `.html`, `.htm` | Chữ trong HTML; bỏ script/style/head, không chạy JavaScript hoặc tải liên kết. |

Các định dạng cần chuyển đổi trước: `.doc` → `.docx`, `.ppt` → `.pptx`, `.xlsb` → `.xlsx`; `.odt/.odp/.ods` → định dạng Office tương ứng. Dùng Save As/Xuất của ứng dụng, không chỉ đổi đuôi tên file. Khi gặp các đuôi này trong thư mục học, chương trình sẽ báo rõ.

JSON của Chat_SFT, bộ nhớ và hồ sơ vẫn dùng cấu trúc riêng; không tự lấy mọi JSON làm dữ liệu Pretrain.

## 2. Xem trước và xuất nội dung

Mở PowerShell tại dự án, thay đường dẫn ví dụ bằng file thật:

```powershell
cd D:\BimBom_AI
.\run.cmd read bimbom "D:\TaiLieu\bai_hoc.docx"
```

Có thể dùng lệnh ngắn `run read bimbom ...` nếu PATH đã nhận. Mặc định hiển thị tối đa 6.000 ký tự. Chỉnh phần xem trước:

```powershell
run read bimbom "D:\TaiLieu\bang_so_lieu.xlsx" --preview-chars 12000
```

Xuất toàn bộ nội dung thành file TXT mới:

```powershell
run read bimbom "D:\TaiLieu\bai_trinh_chieu.pptx" --output "D:\BimBom_AI\Ket_Qua\noi_dung_trich_xuat.txt"
```

`--output` chỉ nhận `.txt`/`.md`; thư mục cha phải tồn tại, file đích phải chưa tồn tại. Không ghi đè nguồn hoặc file đích cũ. Nội dung xuất đầy đủ, không bị cắt theo `--preview-chars`.

Lệnh đọc chưa gọi mô hình để phân tích/trả lời về tài liệu và không tự thêm file vào dữ liệu học.

## 3. Đưa tài liệu vào huấn luyện

Đặt file đã kiểm tra vào:

```text
D:\BimBom_AI\Hoc_BimBom\Du_Lieu_Huan_Luyen\Pretrain
```

Có thể tổ chức thư mục con:

```text
Pretrain/
├── Cach_tra_loi/bai_hoc.docx
├── Phan_tich/phuong_phap.pptx
├── So_lieu/vi_du.xlsx
└── Du_lieu/bang_mau.csv
```

Chương trình đọc cả thư mục con, trích xuất văn bản trong bộ nhớ, kiểm tra, loại nội dung trùng và chia train/validation. Không sửa nội dung file nguồn. Sau khi phiên học hoàn tất, các file đủ điều kiện được chuyển nguyên bản sang `Da_Hoc` theo [hướng dẫn lưu tài liệu đã học](DA_HOC.md). Lệnh đọc thử không chuyển file. File khóa Office bắt đầu bằng `~$` được bỏ qua. File hỏng hoặc định dạng cũ cần chuyển đổi sẽ báo lỗi có đường dẫn, không âm thầm bỏ qua.

```powershell
# Menu chọn học tiếp, tạo mới hoặc học dữ liệu mới:
run train bimbom

# Nạp tài liệu hiện tại và giữ trọng số của checkpoint đã có:
run train bimbom --init-from best --stage pretrain --steps 100
```

Resume dùng dữ liệu đã lưu trong checkpoint nên **không tự nạp file mới**. Muốn nạp tập dữ liệu hiện tại mà giữ trọng số, chọn init-from. Thư mục `Tai_Lieu` chỉ giữ tài liệu gốc, không tự đưa vào train; hội thoại thô, hàng chờ duyệt và Chat_SFT vẫn tách biệt.

Không chép cả file nguồn và bản TXT xuất từ nó chỉ để tăng số lượng dữ liệu: các bản cùng văn bản sau chuẩn hóa sẽ được loại trùng khi đọc.

## 4. Giới hạn nội dung

- Không OCR ảnh hoặc diễn giải biểu đồ, sơ đồ, công thức toán dạng hình và âm thanh/video nhúng.
- Word chưa lấy textbox, header/footer, chú thích và nội dung sửa đổi theo dõi phức tạp. Kiểm tra bản xuất nếu file có bố cục đặc biệt.
- PowerPoint đọc theo thứ tự slide/shape, chưa bảo đảm đúng thứ tự đọc trực quan của mọi bố cục. Có đọc ghi chú người trình bày.
- Excel dùng kết quả công thức đã lưu, không bảo đảm đó là giá trị mới nhất. Với XLSX/XLSM, ô công thức chưa có kết quả được giữ dưới dạng `[Công thức chưa có kết quả lưu: ...]` và có thông báo. Nếu cần số đã tính, tính lại và lưu bằng Excel trước khi đọc.
- PDF nhiều cột/bảng có thể sai thứ tự chữ. Trang không có chữ được thông báo; cả file không có chữ thì dừng và yêu cầu OCR. PDF có mật khẩu cần bản đã mở khóa.
- CSV/TSV nên có tiêu đề cột và đơn vị đo rõ ràng. Bộ đọc kiểm tra các bản ghi hoàn chỉnh với dấu phẩy, chấm phẩy, tab và dấu `|`; dùng tiêu đề rõ ràng khi số cột trong phần thân không đều. Chỉ khi vẫn không xác định được mới thông báo và dùng dấu phẩy.
- Hai cấu trúc từ điển `english,vietnamese_analytics` và `diacritical_marks_vietnamese,no_accents_mark_vietnamese,mean` được nhận diện riêng. Nếu phần nghĩa chứa dấu phẩy chưa được bọc ngoặc kép, bộ đọc giữ các dấu phẩy thừa trong cột nghĩa cuối cùng, chỉ trên bản dữ liệu trong bộ nhớ. File nguồn không bị sửa. Với cấu trúc CSV khác, số cột không đều vẫn được thông báo, không tự gộp hoặc đoán ô bị thiếu.
- Tài liệu vẫn phải đủ nội dung để chia train/validation. Hỗ trợ định dạng mới không bỏ qua kiểm tra chất lượng hoặc Early Stopping.

## 5. Mã hóa và dung lượng

Mỗi đợt có ngân sách tổng riêng; file lỗi hoặc chưa đủ ngân sách được báo và giữ lại. Xem [cấu hình hiện tại và cách nhập từng đợt](TRAIN_NHIEU_FILE.md).

Trong `Chinh_Che_Do.py`:

```python
DOCUMENT_TEXT_ENCODING = "auto"
DOCUMENT_MAX_FILE_MB = 256
DOCUMENT_MAX_ARCHIVE_MB = 512
DOCUMENT_MAX_CHARACTERS = 60000000
DOCUMENT_MAX_CELLS = 2000000
```

`auto` đọc UTF-8 và UTF-16/UTF-32 có BOM cho văn bản/CSV/TSV/HTML. Với mã cũ, ưu tiên lưu lại UTF-8; hoặc đặt mã chính xác như `cp1258`. Không đoán mã hóa khi giải mã bị lỗi. RTF sử dụng codepage trong tài liệu.

Mặc định giới hạn 256 MiB/file, 512 MiB tổng dữ liệu giải nén của Office, 60 triệu ký tự trích xuất/file và 2 triệu ô Excel/CSV. Đọc riêng file vượt giới hạn sẽ báo lỗi; khi quét cả thư mục, file này được thông báo và giữ lại để chia nhỏ. Không âm thầm cắt nội dung. Tổng một đợt còn chịu `IMPORT_MAX_TOTAL_FILE_MB` và `IMPORT_MAX_TOTAL_CHARACTERS`.

## 6. Thư viện và kiểm tra

Đã cài python-docx, python-pptx, openpyxl, xlrd, pypdf và striprtf trong duy nhất `Model_BimBomAI\.venv`. Phiên bản cố định trong `Model_BimBomAI\requirements-documents.txt`; bản đầy đủ trong `requirements.lock.txt`. `setup.ps1` đã cập nhật để cài các thư viện này khi thiết lập lại.

Cài riêng thư viện đọc file nếu cần:

```powershell
cd D:\BimBom_AI
.\Model_BimBomAI\.venv\Scripts\python.exe -m pip install -r Model_BimBomAI\requirements-documents.txt
.\Model_BimBomAI\.venv\Scripts\python.exe -m pip check
```

Kiểm thử các bộ đọc bằng file mẫu tạm, tự dọn sau kiểm thử:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe -B Ket_Qua\Danh_Gia\kiem_tra_doc_tai_lieu_20261118.py
```

Kịch bản không huấn luyện mô hình chính hoặc sửa tài liệu của bạn.
