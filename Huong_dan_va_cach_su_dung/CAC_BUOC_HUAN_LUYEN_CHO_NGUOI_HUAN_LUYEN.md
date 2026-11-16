# Các bước huấn luyện BimBom AI dành cho người huấn luyện

Tài liệu thao tác từng bước, dành cho người chưa quen chạy mô hình. Tất cả lệnh dùng **PowerShell trên Windows**, tại `D:\BimBom_AI`.

[Giới thiệu](GIOI_THIEU.md) | [Sử dụng](CACH_SU_DUNG.md) | [Tóm tắt huấn luyện](HUAN_LUYEN.md)

## Trước khi bắt đầu

Dự án đang ở trạng thái chưa có trọng số đã huấn luyện. Tài liệu này chỉ hướng dẫn thao tác; việc tạo tài liệu không chạy thử, không huấn luyện và không tạo checkpoint.

Có hai chức năng khác nhau:

- **phan_tich.py:** đối chiếu hồ sơ với tiêu chí nghề nghiệp viết sẵn. Dùng ngay được, không học từ tài liệu và không bị thay đổi công thức khi chạy train.py.
- **train.py + chat.py có checkpoint:** mô hình ngôn ngữ nhỏ học dự đoán token tiếp theo. Cần huấn luyện, nhưng chưa bảo đảm phân tích hồ sơ chính xác hoặc làm theo chỉ dẫn.

**Mục tiêu của lần đầu:** chạy được quy trình trên dữ liệu đúng, lưu được kết quả và biết cách đánh giá. Không coi việc chạy xong là bằng chứng AI đã hiểu hoặc tư vấn đúng.

## Bước 1 — Xác định bài học và đầu ra mong muốn

Trước khi chuẩn bị dữ liệu, ghi rõ:

1. AI sẽ nhận thông tin gì? Ví dụ: ngành học, kỹ năng có minh chứng, kinh nghiệm liên quan và mục tiêu của người dùng.
2. AI cần trả lời theo cấu trúc nào? Ví dụ: dữ liệu đã có → thông tin còn thiếu → phân tích có căn cứ → hướng nghề nghiệp → kỹ năng cần bổ sung.
3. Giáo viên dựa vào đâu để đánh giá? Dùng tiêu chí công việc, bài thực hành và tài liệu có nguồn đã kiểm tra.
4. Những gì không được kết luận? Ví dụ: không suy đoán năng lực tổng quát hoặc khẳng định chắc chắn được tuyển khi thiếu bằng chứng.

Bắt đầu với phạm vi hẹp, chẳng hạn phân tích hồ sơ cho một nhóm công việc. Chưa nên gom nhiều loại bài không liên quan vào lần học đầu.

**Hoàn thành bước này khi:** người huấn luyện và giáo viên thống nhất được một dạng đầu vào, một mẫu câu trả lời và cách chấm.

## Bước 2 — Mở PowerShell đúng thư mục

Mở PowerShell, sao chép từng dòng sau và nhấn Enter:

```powershell
cd D:\BimBom_AI
$env:PYTHONIOENCODING = 'utf-8'
Get-Location
```

Kết quả Get-Location phải là `D:\BimBom_AI`. Mở file hướng dẫn từ thư mục con không tự đưa PowerShell về đúng chỗ. Mỗi lần mở PowerShell mới, chạy lại hai dòng đầu.

Không nhập các lệnh PowerShell vào phần chat của BimBom.

## Bước 3 — Kiểm tra Python và GPU

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe Model_BimBomAI\kiem_tra.py
```

Đọc các thông tin được in:

| Trường | Cần kiểm tra |
| --- | --- |
| python | Nhánh 3.13 |
| executable | Trỏ vào Model_BimBomAI\.venv |
| torch, tokenizers | Có phiên bản, không báo thiếu thư viện |
| cuda_available | true nếu muốn dùng GPU |
| device | cuda hoặc cpu theo cấu hình |

Nếu đang dùng auto và CUDA không có, chương trình chọn CPU. Nếu chọn cuda bắt buộc, thiếu GPU sẽ báo lỗi. Máy chạy CPU vẫn dùng được mô hình nhưng tốc độ có thể khác.

Chỉ khi môi trường thiếu hoặc lỗi thư viện, chạy:

```powershell
powershell -ExecutionPolicy Bypass -File .\Model_BimBomAI\setup.ps1 -Backend cuda
```

Máy không có GPU NVIDIA dùng `-Backend cpu`. Sau khi thiết lập, chạy lại kiem_tra.py. Không tạo thêm môi trường .venv khác và không cài thư viện trong lúc đang huấn luyện.

**Hoàn thành bước này khi:** lệnh kiểm tra chạy thành công và thiết bị đúng mong muốn. Kiểm tra môi trường chưa huấn luyện mô hình.

## Bước 4 — Chuẩn bị tài liệu học

Thư mục nhận dữ liệu:

```text
D:\BimBom_AI\Hoc_BimBom
```

Chỉ dùng `.txt` hoặc `.md`, lưu UTF-8. PDF, Word và ảnh cần chuyển nội dung sang văn bản trước. Hồ sơ JSON trong Du_Lieu\Phan_Tich không tự được đọc vào tập huấn luyện.

Tại thời điểm viết hướng dẫn, Hoc_BimBom có một bài hướng dẫn tiếng Việt. Cần bổ sung tài liệu độc lập phù hợp mục tiêu phân tích; chương trình yêu cầu **ít nhất hai tài liệu khác nội dung**. Hai tài liệu chỉ là mức tối thiểu để chạy, không phải lượng đủ để học tốt.

Một file nên chứa một hồ sơ và phân tích đã được kiểm tra. Đặt tên dễ quản lý, ví dụ `ho_so_001_da_kiem_tra.md`. Không dùng tên thật nếu không cần.

Khung nội dung để soạn bài:

```text
Hồ sơ:
- Ngành học: ...
- Kỹ năng và minh chứng: ...
- Kinh nghiệm liên quan: ...
- Mục tiêu nghề nghiệp: ...

Yêu cầu phân tích: ...
Thông tin còn thiếu, cần hỏi thêm: ...
Phân tích có căn cứ: ...
Hướng nghề nghiệp đáng xem xét và lý do: ...
Kỹ năng cần bổ sung và cách kiểm chứng: ...
Giới hạn của kết luận: ...
```

Đây là khung để điền nội dung, không phải bài học hoàn chỉnh. Không đưa file chỉ chứa dấu ba chấm vào tập học.

Trước khi lưu vào Hoc_BimBom:

- Kiểm tra chính tả, số liệu và tính nhất quán giữa hồ sơ với phân tích.
- Xóa bản nháp sai, đoạn lặp, nội dung không liên quan và thông tin cá nhân không cần thiết.
- Chỉ dùng dữ liệu được phép sử dụng và câu trả lời đã được người có chuyên môn kiểm tra.
- Giữ bản giáo viên nhận xét ở Ket_Qua; chỉ đưa phần bài học đã sửa sạch vào Hoc_BimBom.
- Không chép toàn bộ thư mục hướng dẫn vận hành hoặc các file kết quả vào tập học ngoài ý muốn.

**Hoàn thành bước này khi:** có nhiều ví dụ thực chất, ít nhất hai file khác nhau và giáo viên đã kiểm tra nội dung.

## Bước 5 — Tránh lẫn dữ liệu học và dữ liệu đánh giá

Chương trình loại trùng hoàn toàn, xáo trộn theo seed rồi chia khoảng 15% **số tài liệu** làm validation, ít nhất một file. Tokenizer chỉ học từ tập train.

Chương trình chưa nhận ra hai file khác chữ nhưng cùng người hoặc cùng bài. Vì vậy:

1. Gom các thông tin của cùng một người vào một file, không tách biến thể sang nhiều file.
2. Không chép lại cùng hồ sơ và sửa vài từ để tăng số lượng.
3. Chuẩn bị thêm một số hồ sơ để giáo viên kiểm tra riêng, lưu ngoài Hoc_BimBom. Không dùng những hồ sơ này để huấn luyện hoặc chỉnh đáp án mẫu.
4. Khi đã có manifest, kiểm tra nguồn của hai tập có thực sự độc lập không.

Nếu muốn kiểm tra cách chia **trước khi huấn luyện mô hình**, có thể chủ động chạy:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe Model_BimBomAI\hoc_thu_muc.py
```

Lệnh này tạo tokenizer và dữ liệu mã hóa trong `Ket_Qua\Du_Lieu_Da_Xu_Ly\TEN_LAN`, **chưa tạo trọng số mô hình**. Mở manifest.json để xem danh sách train/validation. Nó không còn là thao tác chỉ đọc vì đã tạo file xử lý.

Lệnh train.py về sau sẽ tự chuẩn bị một bộ dữ liệu mới; chưa có cờ nạp trực tiếp thư mục đã chuẩn bị ở bước này. Nếu tài liệu, seed và cấu hình không đổi, cách chia được giữ nhất quán; vẫn kiểm tra manifest của lần học thực tế.

## Bước 6 — Chọn cấu hình lần đầu

Mở `D:\BimBom_AI\Chinh_Che_Do.py`. Khi mới bắt đầu, giữ cấu hình mặc định:

| Thông số | Giá trị |
| --- | --- |
| CHE_DO | auto |
| MODEL_LAYERS / MODEL_DIM / MODEL_HEADS | 4 / 256 / 4 |
| VOCAB_SIZE | 8000, là giới hạn trên |
| CONTEXT_LENGTH | 256 token |
| MICRO_BATCH_SIZE | 2 |
| GRAD_ACCUM_STEPS | 16 |
| LEARNING_RATE | 0.0003 |
| CHECKPOINT_EVERY_STEPS | 200 |
| USE_FP16 | True trên CUDA; CPU dùng FP32 |
| SEED | 42 |

Một optimizer step gồm 16 micro-batch ở cấu hình này. `--steps 100` không có nghĩa là đọc mỗi tài liệu 100 lần. Số token thực tế trong từ vựng có thể nhỏ hơn 8.000 khi dữ liệu ít.

Nếu muốn lưu thường xuyên hơn cho lần đầu, có thể đặt CHECKPOINT_EVERY_STEPS = 20 trước khi chạy. Việc này tăng số checkpoint và dung lượng lưu. Không sửa cấu hình giữa lúc đang học rồi kỳ vọng tiến trình tự đổi theo.

## Bước 7 — Chạy lần huấn luyện đầu tiên

Có hai lựa chọn; không bắt buộc chạy cả hai:

**A. Kiểm tra luồng với mô hình nhỏ, 10 bước:**

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe train.py --smoke --steps 10
```

Lệnh này dùng dữ liệu thật trong Hoc_BimBom nhưng tạo mô hình nhỏ hơn: 1 lớp, dim 32, context 32, batch 1, tích lũy 1. Nó có huấn luyện và tạo checkpoint; kết quả chỉ để kiểm tra luồng. Muốn chuyển sang mô hình chính, chạy mới theo B, không resume từ checkpoint smoke.

**B. Học BimBom Small từ đầu, 100 bước:**

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe train.py --steps 100
```

Không thêm --resume. Mỗi lần chạy tạo thư mục mới, không ghi đè lần cũ. Đọc cấu hình được in lúc đầu để biết thiết bị, số tham số và dữ liệu thực tế.

**Trong lần chuẩn bị tài liệu này, chưa chạy A hoặc B. Bạn chỉ bắt đầu học khi tự chạy lệnh.**

## Bước 8 — Theo dõi trong lúc chạy

Chương trình in số liệu ở bước 0, các mốc lưu và bước cuối. Với chu kỳ lưu 200 và tổng 100 bước, bạn thường chỉ thấy số liệu bước 0 rồi bước 100; khoảng im lặng giữa hai mốc chưa có nghĩa là bị treo.

Có thể mở PowerShell thứ hai để theo dõi GPU:

```powershell
nvidia-smi -l 2
```

Ctrl+C trong cửa sổ theo dõi chỉ dừng theo dõi. Ctrl+C trong cửa sổ huấn luyện sẽ ngắt huấn luyện; phần sau checkpoint gần nhất có thể mất.

Chờ dòng **Hoàn tất:** và ghi lại đường dẫn được in. Không tắt máy hoặc xóa file trong lúc chương trình đang ghi checkpoint.

Nếu thấy lỗi, đọc thông báo và error.log; không coi thư mục mới tạo là lần học thành công chỉ vì nó đã xuất hiện.

## Bước 9 — Ghi lại và kiểm tra kết quả

Ví dụ cấu trúc:

```text
Ket_Qua\Checkpoint_BimBom\TEN_LAN\
  config.json
  metrics.jsonl
  best.json
  step_00000000.pt
  step_00000100.pt
  sample_00000000.txt
  sample_00000100.txt
```

TEN_LAN là tên thư mục thực tế, không nhập nguyên chữ này. Có thể có thêm checkpoint khi thay chu kỳ lưu.

- config.json: kiểm tra thiết bị, số tham số, kiến trúc và cấu hình đã dùng.
- metrics.jsonl: xem train_loss và validation_loss ở từng mốc.
- step_00000000.pt: baseline chưa học.
- step_00000100.pt: trạng thái bước 100, nếu hoàn thành lệnh mẫu.
- best.json: trỏ đến checkpoint tốt nhất theo validation đã đo. Nó có thể chọn bước 0 nếu học làm validation xấu đi.
- sample_*.txt: mẫu văn bản để theo dõi tiến bộ, không tự được coi là đúng.

Một lần resume không cải thiện kỷ lục đã lưu có thể không tạo best.json mới. Khi đó đối chiếu cả lần gốc và lần resume, không tự chọn file mới nhất làm tốt nhất.

| Dấu hiệu | Việc người huấn luyện cần làm |
| --- | --- |
| Train và validation cùng giảm | Tiếp tục kiểm tra bằng hồ sơ độc lập |
| Train giảm, validation tăng | Xem xét học thuộc, dữ liệu hoặc số bước |
| Loss NaN/Inf | Dừng, xem lỗi và cấu hình; chưa dùng kết quả |
| Loss giảm nhưng câu trả lời sai | Ưu tiên đánh giá nội dung, sửa dữ liệu |
| best.json chọn bước 0 | Chưa có mốc học cải thiện validation; không tuyên bố mô hình tiến bộ |

## Bước 10 — Cho giáo viên kiểm tra câu trả lời

Trong PowerShell hiện tại, đặt biến trỏ đến **thư mục thực tế** vừa học:

```powershell
$lanHoc = '.\Ket_Qua\Checkpoint_BimBom\TEN_LAN'
```

Thay TEN_LAN trước khi chạy. Nếu mở PowerShell mới, chạy lại `cd D:\BimBom_AI`, thiết lập UTF-8 và khai báo $lanHoc.

Ví dụ sinh câu trả lời từ bước 100:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe chat.py --checkpoint "$lanHoc\step_00000100.pt" --prompt "Hồ sơ: học công nghệ thông tin, biết Python cơ bản, chưa có kinh nghiệm. Thông tin cần hỏi thêm:" --tokens 100
```

Đây là prompt minh họa, không phải đáp án chuẩn. Mô hình có thể sinh sai hoặc không làm theo yêu cầu. Với context 256 token, không dán hồ sơ quá dài: mô hình chỉ nhìn phần ngữ cảnh gần nhất khi sinh.

Mỗi lượt thành công tự lưu file `Ket_Qua\tra_loi_*.md`, chứa nội dung nhập, kết quả, nguồn checkpoint và phần nhận xét giáo viên. File mẫu sinh trong lúc train vẫn là .txt, không tự thành phiếu kiểm tra Markdown.

Giáo viên kiểm tra:

- Kết luận có dựa đúng thông tin hồ sơ không?
- Có tự bịa kỹ năng, kinh nghiệm hoặc thông tin cá nhân không?
- Có nhận ra thông tin còn thiếu và hỏi thêm đúng trọng tâm không?
- Gợi ý có phù hợp tiêu chí công việc đã thống nhất không?
- Có giải thích giới hạn thay vì khẳng định chắc chắn không?

Điền kết luận Đạt/Cần sửa, căn cứ, phần sai và câu trả lời sửa lại. Giữ cùng một bộ hồ sơ kiểm tra và tiêu chí khi so sánh các checkpoint. Không dùng riêng điểm tự chấm 70/15/15 của phan_tich.py để chứng minh mô hình ngôn ngữ đã học tốt.

## Bước 11 — Đánh giá checkpoint bằng công cụ

Sau khi khai báo $lanHoc như bước 10:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe Model_BimBomAI\danh_gia.py "$lanHoc\step_00000000.pt" "$lanHoc\step_00000100.pt"
```

Công cụ ghi báo cáo JSON vào Ket_Qua\Danh_Gia_BimBom: validation loss, perplexity, mẫu cố định, thời gian sinh và peak VRAM. Chỉ so sánh loss trực tiếp khi dữ liệu và tokenizer giống nhau. Perplexity chặn số mũ ở 80 để tránh tràn số; giá trị rất lớn không phải số chính xác để xếp hạng.

Kết hợp báo cáo định lượng với nhận xét giáo viên. Chưa đủ căn cứ thì tiếp tục cải thiện dữ liệu, không tự nâng kích thước mô hình.

## Bước 12 — Chọn học tiếp hay học lại

### Học tiếp khi giữ nguyên bài học và cấu hình đã lưu

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe train.py --resume "$lanHoc\step_00000100.pt" --steps 300
```

Từ 100 đến 300 là **học thêm 200 bước**. Resume tạo thư mục mới và nạp trạng thái model, optimizer, scaler, RNG, dữ liệu, tokenizer và cấu hình từ checkpoint.

Không đọc lại tài liệu mới trong Hoc_BimBom. Không kết hợp --resume với --smoke hoặc --include-approved. Sửa batch, learning rate hay FP16 trong Chinh_Che_Do.py không tự thay các giá trị đã lưu khi resume; thiết bị vẫn có thể chọn bằng cấu hình hiện tại hoặc --device.

### Học lại khi thay dữ liệu hoặc kiến trúc

Sau khi sửa, kiểm tra lại dữ liệu và chạy:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe train.py --steps 100
```

Lệnh này tạo trọng số mới. Không cần xóa lần cũ để học từ đầu. Giữ lại checkpoint và nhận xét quan trọng nếu muốn so sánh.

### Học thêm các bản ghi đã được duyệt

Chỉ dùng khi đã thực hiện quy trình duyệt kỹ năng trong CACH_SU_DUNG.md:

```powershell
.\Model_BimBomAI\.venv\Scripts\python.exe train.py --include-approved --steps 100
```

Đây vẫn là lần học mới. Sửa nhận xét giáo viên trong Markdown không tự duyệt bản ghi hoặc tự huấn luyện. Không nạp bản nháp chưa xác nhận đúng.

## Bước 13 — Ghi nhật ký mỗi lần học

Người huấn luyện nên ghi riêng một phiếu, có thể lưu Markdown trong Ket_Qua. Nội dung gợi ý:

```text
Ngày và người huấn luyện:
Mục tiêu bài học:
Tài liệu đã thêm/sửa và nguồn:
Seed/cấu hình hoặc đường dẫn config.json:
Lệnh đã chạy:
Thư mục checkpoint:
Checkpoint được chọn và lý do:
Train loss / validation loss:
Bộ hồ sơ kiểm tra của giáo viên:
Các file nhận xét Markdown:
Lỗi còn tồn tại:
Quyết định: học tiếp / sửa dữ liệu / chưa sử dụng:
```

Đây là nhật ký do người huấn luyện viết, không phải file tự sinh. Không đưa nhật ký vận hành vào Hoc_BimBom.

## Xử lý lỗi thường gặp

| Thông báo/tình huống | Cách xử lý |
| --- | --- |
| Không tìm thấy python.exe | Kiểm tra đang ở D:\BimBom_AI và môi trường Model_BimBomAI\.venv còn tồn tại |
| Thiếu torch hoặc tokenizers | Chạy setup.ps1 phù hợp thiết bị, rồi kiểm tra lại môi trường |
| Cần ít nhất 2 tài liệu | Bổ sung nội dung độc lập; file trùng hoàn toàn hoặc rỗng không được tính |
| Lỗi đọc UTF-8 | Lưu lại file dưới dạng UTF-8 |
| CUDA không khả dụng | Kiểm tra cài đặt hoặc dùng CHE_DO cpu/auto |
| Hết VRAM | Với lần mới, giảm micro-batch trước, rồi context hoặc kích thước mô hình nếu cần |
| Loss/gradient không hữu hạn | Dừng; kiểm tra dữ liệu, giảm learning rate hoặc thử FP32 cho lần mới |
| Không tìm thấy checkpoint | Chọn đúng file .pt đã ghi hoàn chỉnh, không dùng tên TEN_LAN mẫu |
| Resume báo steps không đủ | Nhập tổng số bước lớn hơn step đã lưu |
| Không có dòng tiến độ mới ngay | Xem chu kỳ CHECKPOINT_EVERY_STEPS; theo dõi GPU và chờ mốc kế tiếp |
| Không lưu được Markdown | Kiểm tra quyền ghi/dung lượng Ket_Qua; sao chép nội dung màn hình trước khi đóng |

Không có thư mục tests hay Sao_Luu trong bản dự án gọn hiện tại. Trước khi chủ động xóa checkpoint hoặc báo cáo, hãy lưu riêng những kết quả quan trọng. Không xóa tài liệu gốc hoặc nhận xét giáo viên chỉ để bắt đầu một lần học mới.

## Danh sách hoàn tất lần đầu

- [ ] Mục tiêu phân tích và tiêu chí giáo viên đã rõ.
- [ ] Python/thư viện/thiết bị được kiểm tra thành công.
- [ ] Có ít nhất hai tài liệu độc lập, nội dung đã kiểm tra.
- [ ] Dữ liệu học và hồ sơ kiểm tra độc lập không bị trùng người/nội dung.
- [ ] Đã chạy đúng lệnh học từ đầu khi sẵn sàng.
- [ ] Có checkpoint hoàn chỉnh và đã ghi lại thư mục.
- [ ] Đã đọc metrics và kiểm tra manifest.
- [ ] Giáo viên đã nhận file Markdown và ghi nhận xét.
- [ ] Quyết định học tiếp hay sửa dữ liệu dựa trên cả số liệu và nội dung.
