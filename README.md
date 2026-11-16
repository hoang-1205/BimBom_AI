# BimBom AI — Bắt đầu từ trạng thái chưa huấn luyện

## Trạng thái bàn giao

Dự án chưa có checkpoint, tokenizer đã học, chỉ mục tra cứu hay kết quả huấn luyện. Không chạy huấn luyện trong lần chuẩn bị này. Mã, môi trường Python, tài liệu gốc và cấu hình được giữ lại. Bộ kiểm thử, bản sao lưu và kế hoạch nâng cấp cũ đã được gỡ để dự án gọn hơn.

## Bạn muốn làm gì?

- [Hiểu chức năng và giới hạn](Huong_dan_va_cach_su_dung/GIOI_THIEU.md)
- [Phân tích hồ sơ, tra cứu và gửi kết quả cho giáo viên](Huong_dan_va_cach_su_dung/CACH_SU_DUNG.md)
- [Chuẩn bị dữ liệu và huấn luyện từ đầu](Huong_dan_va_cach_su_dung/HUAN_LUYEN.md)
- [Các bước chi tiết dành cho người huấn luyện](Huong_dan_va_cach_su_dung/CAC_BUOC_HUAN_LUYEN_CHO_NGUOI_HUAN_LUYEN.md)

## Thư mục

```text
D:\BimBom_AI\
├── Hoc_BimBom\                     Tài liệu học và tra cứu
├── Ket_Qua\                        Kết quả và file Markdown cho giáo viên
├── Du_Lieu\Phan_Tich\              Hồ sơ mẫu và tiêu chí nghề nghiệp
├── Huong_dan_va_cach_su_dung\       Tài liệu giới thiệu, sử dụng và huấn luyện
├── Model_BimBomAI\                  Mã hỗ trợ, setup và môi trường .venv
├── Chinh_Che_Do.py                  Cấu hình CPU/CUDA và mô hình
├── phan_tich.py                     Phân tích theo tiêu chí, không cần huấn luyện
├── train.py                         Huấn luyện mô hình ngôn ngữ
├── chat.py                          Chat, tra cứu và tìm kỹ năng
└── README.md                       Đọc đầu tiên
```

Các thư mục checkpoint, tokenizer, chỉ mục và kho kỹ năng chỉ được tạo khi sử dụng. Hoc_BimBom và Ket_Qua nằm cùng cấp ngoài thư mục gốc.

## Lệnh đầu tiên

Mở PowerShell:

```powershell
cd D:\BimBom_AI
$env:PYTHONIOENCODING = 'utf-8'
.\Model_BimBomAI\.venv\Scripts\python.exe Model_BimBomAI\kiem_tra.py
```

Kiểm tra môi trường không huấn luyện mô hình. Đọc HUAN_LUYEN.md trước khi chạy train.py. Phân tích theo tiêu chí và tra cứu tài liệu dùng được khi chưa có mô hình đã học.

