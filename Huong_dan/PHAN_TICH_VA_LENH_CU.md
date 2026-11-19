# Phân tích hồ sơ và các lệnh cũ

[Giới thiệu](GIOI_THIEU.md) | [Cách sử dụng hiện tại](CACH_SU_DUNG.md)

## 1. Mở dự án

Đối với chat và huấn luyện mới, dùng `run chat bimbom` / `run train bimbom` theo [hướng dẫn mới](CACH_SU_DUNG.md). Trang này giữ hướng dẫn phân tích hồ sơ và các lệnh `chat.py`, `ky_nang.py` cũ. Kho kỹ năng cũ trong `Du_Lieu` tách biệt với hàng chờ và Chat_SFT mới; không tự nhập vào dữ liệu huấn luyện.

Mở PowerShell và chạy mỗi khi bắt đầu phiên mới:

```powershell
cd D:\BimBom_AI
$env:PYTHONIOENCODING = 'utf-8'
```

Các lệnh sau dùng Python hiện có trong Model_BimBomAI\.venv. Nếu môi trường lỗi, xem [hướng dẫn chính](CACH_SU_DUNG.md).

## 2. Phân tích hồ sơ khi chưa huấn luyện

Chạy thử bằng hồ sơ minh họa khi bạn muốn:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe phan_tich.py
```

Để phân tích hồ sơ riêng, sao chép `Du_Lieu\Phan_Tich\ho_so_mau.json` thành `ho_so_cua_toi.json`, sửa và lưu UTF-8:

```json
{
  "nganh_hoc": ["Công nghệ thông tin"],
  "ky_nang": {"Python": 3, "SQL": 2, "Excel": 3},
  "kinh_nghiem_lien_quan": {"phan_tich_du_lieu": 1}
}
```

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe phan_tich.py .\Du_Lieu\Phan_Tich\ho_so_cua_toi.json
```

Quy ước mức kỹ năng gợi ý: 0 chưa có, 1 mới biết, 2 làm có hướng dẫn, 3 tự làm việc thông thường, 4 xử lý việc khó, 5 hướng dẫn người khác. Không biết mức thì bỏ mục đó, không tự điền 0. Ngành học chưa cung cấp dùng `[]`. Kinh nghiệm là số năm liên quan với từng mã nghề, có thể dùng 0.5; không khai báo được ghi là thiếu thông tin.

Sửa tiêu chí trong `Du_Lieu\Phan_Tich\tieu_chi_nghe.json` theo công việc thực tế. Tên kỹ năng/ngành học phải cùng cách gọi với tiêu chí; chương trình chuẩn hóa chữ hoa thường và khoảng trắng, chưa hiểu từ đồng nghĩa. Mỗi mã nghề phải duy nhất, mức kỹ năng mục tiêu lớn hơn 0 đến 5, số năm mục tiêu lớn hơn 0.

Công thức: trung bình tỷ lệ kỹ năng đạt mức mục tiêu × 70, cộng 15 nếu ngành học trùng, cộng tỷ lệ năm kinh nghiệm đạt mục tiêu × 15. Các tỷ lệ tối đa bằng 1. Thiếu thông tin chưa được cộng điểm; độ đầy đủ dữ liệu không phải độ tin cậy thống kê. Đừng so thứ hạng khi các nghề thiếu dữ liệu không đều.

## 3. File Markdown cho giáo viên

Sau mỗi lần phân tích thành công, chương trình lưu:

- Bản `.md` trực tiếp trong `D:\BimBom_AI\Ket_Qua` để giáo viên đọc.
- Bản JSON chi tiết trong `Ket_Qua\Ket_qua_BimBom`.

Mỗi lượt dùng `chat.py` cũ để chat, tra cứu hoặc tìm kỹ năng cũng tự tạo file `.md` mới trong Ket_Qua. Không cần cờ lưu; không ghi đè file cũ. Tên bắt đầu bằng `phan_tich_` hoặc `tra_loi_`, kèm thời gian và mã riêng. Bộ chạy `run chat bimbom` mới lưu JSONL theo hướng dẫn mới.

File gồm nội dung người dùng cung cấp, kết quả BimBom, nguồn và phần nhận xét. Giáo viên điền người kiểm tra, ngày, kết luận, căn cứ và phần sửa. Mặc định là **Chờ giáo viên kiểm tra**. Ghi nhận xét không tự duyệt kỹ năng, không tự đưa nội dung vào dữ liệu học.

Chỉ các nội dung nhập trong chương trình BimBom được lưu; không thu thập cuộc trò chuyện Codex. Chương trình không tự gửi file cho giáo viên. Báo lỗi nếu không ghi được file; kiểm tra đường dẫn được in sau khi chạy.

## 4. Tra cứu tài liệu khi chưa huấn luyện

Đặt tài liệu TXT/MD UTF-8 đã kiểm tra vào `Hoc_BimBom\Du_Lieu_Huan_Luyen\Pretrain` rồi chạy:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe chat.py --rag --prompt "Cách trả lời tiếng Việt"
```

Bỏ --prompt để nhập nhiều lượt, gõ `/thoat` để kết thúc. Công cụ tìm tối đa ba đoạn theo từ trùng và hiển thị nguồn; chỉ mục tự cập nhật khi truy vấn phát hiện tài liệu thay đổi. Không tìm thấy thì báo rõ. Đây là tra cứu, chưa phải hiểu ngữ nghĩa hoặc suy luận từ mô hình đã học.

## 5. Dùng mô hình sau khi đã huấn luyện

Hiện chưa có checkpoint nên chưa chạy được lệnh dưới. Sau khi huấn luyện theo [hướng dẫn chính](CACH_SU_DUNG.md), thay TEN_LAN bằng tên thư mục kết quả thực tế:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe chat.py --checkpoint ".\Ket_Qua\Checkpoint_BimBom\TEN_LAN\step_00000100.pt" --prompt "BimBom" --tokens 100
```

Mô hình sinh tiếp đoạn mở đầu. Mỗi lượt độc lập; bỏ --prompt để chat và gõ `/thoat` để thoát. --tokens là số token mới, không phải ký tự. Thêm --rag để đưa đoạn tra cứu vào ngữ cảnh; nguồn không chứng minh câu sinh đúng. Thêm --save-draft nếu muốn lưu thêm JSON vào kho bản nháp; bản Markdown vẫn tự lưu mặc định.

## 6. Lưu và duyệt kỹ năng

Tạo `Ket_Qua\cau_tra_loi.txt` UTF-8 chứa câu trả lời đã chuẩn bị. Có thể tạo thêm `Ket_Qua\quy_trinh.txt` chứa cách làm và cách kiểm tra.

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe Model_BimBomAI\ky_nang.py luu --question "Câu hỏi cần lưu" --answer-file ".\Ket_Qua\cau_tra_loi.txt"
.\Model_BimBomAI\.venv\Scripts\python.exe Model_BimBomAI\ky_nang.py danhsach
```

Có quy trình riêng thì thêm --workflow-file ".\Ket_Qua\quy_trinh.txt" vào lệnh luu. Bản nháp nằm trong `Du_Lieu\Ky_Nang_BimBom_Hoc_Duoc\Ban_Nhap`. Đọc, sửa và kiểm tra nội dung; giữ id/status và cú pháp JSON hợp lệ.

Chỉ sau khi người kiểm tra xác nhận đúng, thay ID_BAN_NHAP bằng tên tệp không có .json:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe Model_BimBomAI\ky_nang.py duyet ID_BAN_NHAP --confirm DA_KIEM_TRA
.\Model_BimBomAI\.venv\Scripts\python.exe chat.py --skills --prompt "Câu hỏi cần lưu"
```

Duyệt chuyển bản ghi sang Da_Duyet. Không tự chép JSON sang thư mục này. Sửa bản đã duyệt cần tạo bản nháp mới và duyệt lại. Tìm kiếm chỉ đọc bản đã duyệt; gợi ý gần giống cần kiểm tra. Kho kỹ năng không tự thực thi quy trình.

