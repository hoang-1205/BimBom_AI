# Huấn luyện BimBom AI từ đầu

[Giới thiệu](GIOI_THIEU.md) | [Sử dụng](CACH_SU_DUNG.md) | [Huấn luyện](HUAN_LUYEN.md)

[Hướng dẫn từng bước dành cho người huấn luyện](CAC_BUOC_HUAN_LUYEN_CHO_NGUOI_HUAN_LUYEN.md).

## 1. Điểm xuất phát

Chưa có trọng số, tokenizer đã học hoặc checkpoint. Không cần xóa thêm file trước khi học. Mỗi lần train.py không có --resume sẽ khởi tạo trọng số ngẫu nhiên và tạo thư mục mới.

Chức năng phan_tich.py dùng tiêu chí viết sẵn và không cần huấn luyện. Pipeline ở đây là mô hình ngôn ngữ dự đoán token tiếp theo; huấn luyện không tự thay công thức chấm điểm hồ sơ, không bảo đảm mô hình biết tư vấn nghề nghiệp.

## 2. Kiểm tra môi trường

Mở PowerShell:

```powershell
cd D:\BimBom_AI
$env:PYTHONIOENCODING = 'utf-8'
.\Model_BimBomAI\.venv\Scripts\python.exe Model_BimBomAI\kiem_tra.py
```

Dùng một môi trường Python 3.13 tại Model_BimBomAI\.venv. Nếu máy nhận GPU, kết quả có cuda_available: true. Kiểm tra này không huấn luyện.

Chỉ khi thư viện thiếu hoặc lỗi, chạy thiết lập:

```powershell
powershell -ExecutionPolicy Bypass -File .\Model_BimBomAI\setup.ps1 -Backend cuda
```

Script cài PyTorch 2.9.1+cu128 và tokenizers 0.22.1; ghi phiên bản thực tế trong Model_BimBomAI\requirements.lock.txt. Máy không có GPU có thể dùng -Backend cpu. Không cài lại khi đang huấn luyện.

## 3. Cấu hình thiết bị

Sửa Chinh_Che_Do.py:

- CHE_DO = "auto": ưu tiên CUDA, không có thì CPU.
- CHE_DO = "cpu": chỉ CPU.
- CHE_DO = "cuda": bắt buộc CUDA; không có thì báo lỗi.

Mặc định mô hình: 4 lớp, dim 256, 4 heads, context 256, vocab tối đa 8.000. Micro-batch 2, tích lũy 16 lần mỗi optimizer step, learning rate 0.0003, lưu mỗi 200 bước. FP16 dùng trên CUDA, CPU dùng FP32. Giữ cấu hình ban đầu khi mới bắt đầu; thay đổi kiến trúc chỉ dùng cho lần học mới.

## 4. Chuẩn bị tài liệu học

Đặt ít nhất **hai tài liệu khác nội dung** vào `D:\BimBom_AI\Hoc_BimBom`. Hiện thư mục có bài hướng dẫn tiếng Việt; cần bổ sung dữ liệu phù hợp mục tiêu phân tích. Nhận TXT/MD UTF-8; PDF, Word, ảnh phải chuyển sang văn bản trước. JSON hồ sơ trong Du_Lieu\Phan_Tich không tự được nhập vào tập học.

Để nghiên cứu phân tích nghề nghiệp, mỗi ví dụ nên gồm:

```text
Hồ sơ: ngành học, kỹ năng kèm minh chứng, kinh nghiệm liên quan.
Yêu cầu: mục tiêu phân tích.
Dữ liệu còn thiếu: những thông tin cần hỏi thêm.
Phân tích có căn cứ: từng nhận định và minh chứng.
Hướng nghề nghiệp đáng xem xét: lý do phù hợp và điều kiện.
Kỹ năng cần bổ sung: cách học và cách kiểm chứng.
Giới hạn kết luận: điều chưa thể xác định.
```

Dùng câu trả lời đã được người có chuyên môn kiểm tra, không học từ bản nháp chưa duyệt. Không nhân bản khung rỗng hoặc lặp bài để đủ dữ liệu. Chỉ sử dụng hồ sơ được phép dùng; loại thông tin định danh không cần thiết.

Pipeline loại trùng hoàn toàn và chia validation theo tài liệu (~15%, ít nhất một tài liệu), tokenizer chỉ học từ train. Chưa phát hiện gần trùng hoặc cùng người: chuẩn bị mỗi hồ sơ một file, tránh biến thể của cùng người ở hai tập và kiểm tra manifest sau khi chuẩn bị. Dữ liệu được nạp vào RAM.

## 5. Bắt đầu học

Sau khi đủ dữ liệu:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe train.py --steps 100
```

Đây là 100 **optimizer steps**; mỗi step mặc định gồm 16 micro-batch. Không thêm --resume nếu muốn từ đầu. Không có bộ tests hoặc dữ liệu thử đi kèm nữa.

Nếu muốn kiểm tra luồng bằng mô hình nhỏ trước, bạn có thể chủ động chạy:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe train.py --smoke --steps 10
```

Lệnh --smoke cũng dùng tài liệu trong Hoc_BimBom và tạo checkpoint, nhưng kiến trúc nhỏ hơn; nó không phải mô hình chính. Chúng tôi chưa chạy lệnh này sau lần chuẩn bị hiện tại.

## 6. Xem kết quả

Chương trình in thư mục `Ket_Qua\Checkpoint_BimBom\TEN_LAN` khi hoàn tất. Lưu lại tên này.

| File | Ý nghĩa |
| --- | --- |
| step_00000000.pt | Trạng thái trước học |
| step_00000100.pt | Checkpoint ở bước 100 khi chạy lệnh mẫu |
| config.json | Kiến trúc, thiết bị, cấu hình và phiên bản |
| metrics.jsonl | Loss train/validation, perplexity, tốc độ và VRAM |
| best.json | Trỏ đến checkpoint có validation loss tốt nhất được đo; có thể là bước 0 |
| sample_XXXXXXXX.txt | Mẫu sinh từ prompt cố định |
| error.log | Lỗi nếu lần chạy thất bại hoặc bị ngắt |

Tokenizer, token và manifest nguồn được lưu trong Ket_Qua\Du_Lieu_Da_Xu_Ly. Nếu train loss giảm nhưng validation loss tăng, có dấu hiệu học thuộc: cải thiện dữ liệu trước khi học dài. Chỉ số tốt không chứng minh phân tích nghề nghiệp đúng; đánh giá thêm trên hồ sơ độc lập do giáo viên kiểm tra.

Các file huấn luyện là .pt/.json/.txt; chức năng lưu Markdown cho giáo viên áp dụng khi chat hoặc phân tích hồ sơ, không tự chuyển toàn bộ log huấn luyện thành Markdown.

## 7. Học tiếp và dùng mô hình

Thay TEN_LAN bằng thư mục checkpoint thực tế:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe train.py --resume ".\Ket_Qua\Checkpoint_BimBom\TEN_LAN\step_00000100.pt" --steps 300
```

300 là tổng bước cần đạt: từ 100 học thêm 200. Resume lấy lại model, optimizer, scaler, RNG, tokenizer, dữ liệu và cấu hình đã lưu; không đọc tài liệu mới. Mỗi lần resume tạo thư mục kết quả riêng. Muốn học dữ liệu thay đổi thì chạy mới không có --resume. Không kết hợp resume với --smoke hoặc --include-approved.

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe chat.py --checkpoint ".\Ket_Qua\Checkpoint_BimBom\TEN_LAN\step_00000100.pt" --prompt "BimBom" --tokens 100
```

Kết quả chat tự lưu Markdown trong Ket_Qua để giáo viên nhận xét. Chưa có bảo đảm mô hình làm theo yêu cầu phân tích; mỗi lượt chat hiện độc lập.

## 8. Học nội dung đã duyệt và đánh giá

Sau khi có bản ghi đã duyệt trong kho kỹ năng, có thể đưa vào một lần học mới:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe train.py --include-approved --steps 100
```

Chỉ file đã qua quy trình duyệt mới được lấy từ kho; nhận xét trong Markdown không tự trở thành bản đã duyệt. Không chép bản nháp vào Hoc_BimBom ngoài ý muốn.

So sánh checkpoint dùng cùng dữ liệu/tokenizer:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe Model_BimBomAI\danh_gia.py ".\Ket_Qua\Checkpoint_BimBom\TEN_LAN\step_00000000.pt" ".\Ket_Qua\Checkpoint_BimBom\TEN_LAN\step_00000100.pt"
```

Báo cáo JSON ở Ket_Qua\Danh_Gia_BimBom. Perplexity dùng số mũ chặn ở 80 để tránh tràn số; giá trị cực lớn không phù hợp để xếp hạng chính xác.

## 9. Dừng, lỗi và đặt lại

- Ctrl+C dừng học; phần chưa đến mốc lưu có thể mất. Dùng checkpoint hoàn chỉnh gần nhất để tiếp tục.
- Thiếu tài liệu: bổ sung ít nhất hai tài liệu khác nhau; không sao chép lặp để vượt kiểm tra.
- Thiếu checkpoint: hoàn thành huấn luyện trước khi dùng chat --checkpoint.
- CUDA không khả dụng: kiểm tra môi trường hoặc chọn cpu/auto.
- Hết VRAM: giảm micro-batch, context hoặc kích thước mô hình cho lần mới. FP16 không ổn định: thử USE_FP16 = False. Thay cấu hình ngoài file không tự thay cấu hình đã lưu khi resume.
- Muốn đặt lại: dừng chương trình, xóa các lần học không cần và dữ liệu đã xử lý tương ứng trong Ket_Qua. Giữ file Markdown có nhận xét giáo viên và tài liệu nguồn nếu còn cần.

Không có sao lưu cũ trong dự án sau lần dọn này. Hãy tự lưu riêng các checkpoint hoặc báo cáo quan trọng trước khi xóa.

