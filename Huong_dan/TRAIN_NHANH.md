# Quy trình train rút gọn

## 1. Chuẩn bị tài liệu

Đặt tài liệu đã kiểm tra vào `Hoc_BimBom/Du_Lieu_Huan_Luyen/Pretrain`. File trong các thư mục con cũng được đọc. `Da_Hoc` không tự được đưa vào tập học mới. Muốn tái sử dụng file đã lưu tại đó, chủ động đưa file trở lại Pretrain.

Chương trình tạm bỏ qua file trùng, dòng dài lặp trong train hoặc trùng validation. Với lựa chọn 3, nội dung đã có trong `Da_Hoc` cũng được bỏ qua trước khi chia tập. Báo cáo `Du_lieu_trung.md` ghi nội dung, vị trí và lý do bỏ qua. File gốc không bị sửa. Nếu sau lọc còn quá ít dữ liệu độc lập, cần bổ sung nội dung khác nhau trước khi học. Xem [quy tắc và báo cáo dữ liệu trùng](DU_LIEU_TRUNG.md).

## 2. Chọn đúng cách học

```powershell
cd D:\BimBom_AI
run train bimbom
```

| Mục đích | Lựa chọn |
| --- | --- |
| Học tài liệu mới, giữ trọng số đã có | **3** |
| Học tiếp một phiên đang dở, dùng đúng tập cũ | **1** |
| Khởi tạo mô hình mới từ đầu | **2** |
| Thoát trước khi chạy | **0** |

Với lựa chọn **3**, nhấn **Enter** ở câu hỏi checkpoint để dùng `best`; cũng có thể nhập đường dẫn `.pt` cụ thể. `best` là checkpoint đã xác minh có validation loss tốt nhất trên cùng dữ liệu/tokenizer với checkpoint gần nhất tương thích. Điểm đó thuộc dữ liệu cũ, không bảo đảm tốt nhất trên tài liệu mới. Nếu không có checkpoint phù hợp, chương trình dừng và không tự tạo trọng số mới.

Nếu chọn **1** nhưng có file thêm/sửa, menu cho phép chọn **3** để học tập tài liệu hiện tại, **1** để vẫn học tập cũ, **9** quay lại menu hoặc **0** thoát. Việc thiếu file do đã chuyển sang `Da_Hoc` không tự kích hoạt yêu cầu học lại.

Mặc định hiện tại là `warn`: có thể resume checkpoint từng chạm Early Stopping và tiếp tục đủ số bước yêu cầu, không đặt lại trọng số hoặc lịch sử đánh giá. Nếu chủ động dùng `--early-stopping stop`, bộ chạy vẫn kiểm tra ngưỡng dừng trước khi mở phiên như trước. Xem [train đủ số bước](TRAIN_DU_SO_BUOC.md).

## 3. Chọn số bước học thêm

Nhấn **Enter** để dùng mặc định **200 bước**, hoặc nhập một số khác trong giới hạn được hiển thị. Đây là số **học thêm**, không phải tổng bước của checkpoint. 200 chỉ là mặc định để chạy một phiên ngắn rồi kiểm tra kết quả, không phải số tối ưu được tính theo kích thước dữ liệu.

- Tối thiểu 1, tối đa 100000 theo cấu hình hiện tại.
- Từ 10000 bước cần `HOC_TIEP`; có thể nhập số khác để điều chỉnh hoặc `0` để thoát.
- Trước khi bắt đầu, xem nguồn trọng số, số tài liệu, số bước, thiết bị, batch, tích lũy và learning rate.
- Resume giữ cấu hình huấn luyện trong checkpoint. Tạo mới/init-from dùng cấu hình hiện tại trong `Chinh_Che_Do.py`.

Đổi mặc định Enter trong `Chinh_Che_Do.py`:

```python
TRAIN_DEFAULT_ADDITIONAL_STEPS = 200
```

Giá trị mặc định vẫn chịu giới hạn tối đa và yêu cầu xác nhận số bước lớn.

## 4. Theo dõi và kết thúc

Theo dõi validation loss và cảnh báo overfitting. Không tăng số bước chỉ để bỏ qua việc chất lượng đang giảm. Ctrl+C hoặc `run stop bimbom` yêu cầu dừng an toàn. Phiên hoàn tất đủ điều kiện sẽ chuyển tài liệu đã dùng sang `Da_Hoc`; xem [quy tắc chuyển file](DA_HOC.md).

## Lệnh tắt khi đã biết cách học

```powershell
# Học tập tài liệu hiện tại từ best, thêm 200 bước:
run train bimbom --init-from best --steps 200

# Tiếp tục tập dữ liệu cũ, thêm 200 bước:
run train bimbom --resume --steps 200
```

Lệnh có `--resume` không tự chuyển sang init-from khi có file mới. Chế độ `warn` chỉ cảnh báo khi validation xấu đi và vẫn giữ best riêng; `stop` mới dừng sớm theo validation. Các kiểm tra dữ liệu, checkpoint, tokenizer và NaN/Inf vẫn hoạt động ở cả hai chế độ.
