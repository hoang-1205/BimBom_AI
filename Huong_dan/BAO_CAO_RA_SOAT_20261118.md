# Rà soát train và sử dụng BimBom — 18/11/2026

Đã sửa các lỗi phát hiện trong luồng train, chat, đọc tài liệu, bộ nhớ và tra cứu. Các lần huấn luyện kiểm thử dùng dữ liệu tạm và mô hình nhỏ, chỉ sử dụng Python trong `Model_BimBomAI/.venv`.

## Những phần đã sửa

| Vấn đề | Xử lý |
| --- | --- |
| Lấy mẫu train quét toàn bộ token ở mỗi micro-batch, gây chậm và tạo mảng tạm lớn | Pretrain lấy mẫu trực tiếp; SFT lập chỉ mục token đích một lần rồi tái sử dụng cho train/validation. Không đổi số bước hay batch đang cấu hình. |
| CSV có ô dài hơn giới hạn mặc định của Python bị lỗi dù file còn trong giới hạn BimBom | Dùng giới hạn ký tự của cấu hình tài liệu, vẫn kiểm tra số ô, tổng ký tự và dung lượng. |
| Resume hoặc status thất bại vì một tài liệu mới hỏng | Resume tiếp tục dùng dữ liệu đã lưu trong checkpoint và cảnh báo về file mới; status trả trạng thái cùng `document_error`. Init-from vẫn kiểm tra dữ liệu mới bình thường. |
| Một file bộ nhớ hoặc bản nháp JSON hỏng chặn các ghi nhớ hợp lệ | Bỏ qua file lỗi, thông báo đường dẫn, giữ file nguyên vẹn; không tự sửa/xóa hoặc dùng dữ liệu chưa hợp lệ. |
| Thông số sinh câu trả lời NaN/Inf hoặc temperature quá nhỏ gây lỗi xác suất | Kiểm tra giá trị hữu hạn, lấy mẫu ổn định; chat vẫn cho nhập lệnh sau lỗi sinh câu trả lời và hướng dẫn khi thiếu bộ nhớ GPU. |
| File trạng thái hoặc yêu cầu dừng bị hỏng làm gián đoạn phiên | Không coi dữ liệu JSON hỏng là yêu cầu dừng hợp lệ; phiên đang giữ khóa vẫn được nhận biết là bận. |
| Checkpoint có hệ số optimizer NaN/Inf hoặc ngoài giới hạn được nạp quá muộn | Từ chối ngay khi kiểm tra checkpoint trước resume. |
| Nhiều đáp án của cùng một câu hỏi SFT bị chia sang cả train và validation | Gom theo câu hỏi đã chuẩn hóa rồi chia; yêu cầu ít nhất hai câu hỏi khác nhau. |
| Chỉ mục tra cứu bị hỏng làm dừng RAG | Tạo lại chỉ mục từ tài liệu nguồn; ghi chỉ mục bằng file tạm rồi thay thế. |

## Kết quả kiểm tra

- 86 kiểm thử toàn bộ đã đạt; sau đó 2 kiểm thử riêng cho lỗi chỉ mục tra cứu cũng đạt: tổng cộng **88 kiểm thử**.
- Có smoke test CUDA, kiểm tra NaN/Inf, Early Stopping, Ctrl+C, lưu/resume và SFT thực sự trên mô hình nhỏ.
- Kiểm tra bộ đọc Word/PowerPoint/Excel/CSV/PDF, lọc trùng, báo cáo Markdown và chuyển file sang `Da_Hoc` trên file tạm.
- Đã kiểm tra checkpoint thật `20261118_141107_491858/step_00000200.pt`: nạp hợp lệ, sinh thử một câu ngắn trên CPU thành công. Đây là kiểm tra hoạt động, không phải đánh giá chất lượng câu trả lời.
- Đối chiếu 289 file checkpoint, tài liệu, bộ nhớ và ví dụ hiện có: không thay đổi dung lượng hoặc thời gian ghi. Không chạy train dài hoặc chạy học trên tập dữ liệu thật trong đợt rà soát.

Nhật ký: [kiểm thử toàn bộ](../Ket_Qua/Danh_Gia/ket_qua_kiem_thu_toan_bo_20261118.log), [kết quả kiểm tra checkpoint thật](../Ket_Qua/Danh_Gia/ket_qua_ra_soat_thuc_te_20261118.json).

## Tiếp tục sử dụng

```powershell
run status bimbom
run train bimbom
run chat bimbom
```

File bộ nhớ bị báo lỗi vẫn ở nguyên chỗ để xem và sửa. Báo lỗi tài liệu hiện tại khi resume không có nghĩa checkpoint bị hỏng. Early Stopping, từ chối dữ liệu quá ngắn và bỏ qua dữ liệu trùng vẫn là các bảo vệ đang hoạt động.

Để chạy lại kiểm thử:

```powershell
cd D:\BimBom_AI
$env:PYTHONIOENCODING = 'utf-8'
.\Model_BimBomAI\.venv\Scripts\python.exe -B -m unittest discover -s Ket_Qua\Danh_Gia -p 'kiem_tra_*20261118.py' -v
```

Đóng phiên chat/train đang chạy trước khi thực hiện kiểm thử khóa phiên.
