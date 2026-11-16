# Giới thiệu BimBom AI

[Giới thiệu](GIOI_THIEU.md) | [Sử dụng](CACH_SU_DUNG.md) | [Huấn luyện](HUAN_LUYEN.md)

## Mục tiêu

Hỗ trợ đối chiếu ngành học, kỹ năng, mức năng lực tự khai báo và kinh nghiệm liên quan với tiêu chí công việc; trình bày kết quả và phần còn thiếu để giáo viên kiểm tra.

## Hai phần riêng biệt

| Phần | Cách hoạt động | Cần huấn luyện? |
| --- | --- | --- |
| phan_tich.py | Chấm điểm theo tiêu chí nghề viết sẵn | Không |
| train.py và chat.py có checkpoint | Transformer học dự đoán token tiếp theo | Có |
| chat.py --rag | Tra cứu từ khóa trong tài liệu, kèm nguồn | Không cần checkpoint nếu chỉ tra cứu |
| chat.py --skills | Tìm câu trả lời/kỹ năng đã được duyệt | Không |

Phần chấm điểm hiện chưa phải mô hình đã học cách đánh giá con người. Mô hình ngôn ngữ hiện chưa có trọng số được huấn luyện. Đổi tiêu chí chấm điểm không cập nhật trọng số; chạy train.py cũng không thay công thức của phan_tich.py.

## Phân tích theo tiêu chí

- Hồ sơ gồm ngành học, mức kỹ năng 0–5 và số năm kinh nghiệm liên quan theo từng nghề.
- Điểm mẫu: kỹ năng tối đa 70, ngành học 15, kinh nghiệm 15.
- Kết quả gồm điểm thành phần, mức đầy đủ dữ liệu, kỹ năng đạt/chưa đạt mục tiêu và thông tin chưa khai báo.
- Tiêu chí của ba nghề mẫu là minh họa, cần chỉnh theo công việc thực tế.

Điểm không phải xác suất thành công, quyết định tuyển dụng hay đánh giá năng lực tổng quát. Thiếu thông tin không chứng minh thiếu năng lực. Cần đối chiếu bài thực hành và minh chứng kinh nghiệm.

## Giáo viên kiểm tra

Mỗi lượt chat hoặc phân tích hồ sơ tự lưu file Markdown trong Ket_Qua, gồm đầu vào, kết quả, nguồn và mục nhận xét. Tệp mặc định chờ kiểm tra. Giáo viên sửa nhận xét không tự làm AI học thêm; việc duyệt kỹ năng và huấn luyện là các bước riêng.

## Trạng thái hiện tại

Chưa có checkpoint, tokenizer đã huấn luyện, kết quả cũ hoặc kỹ năng đã duyệt. Môi trường Python và mã đã sẵn có; tài liệu gốc vẫn được giữ. Bộ tests, Sao_Luu và kế hoạch cũ đã được gỡ. Các thư mục phát sinh sẽ được chương trình tạo khi dùng.
