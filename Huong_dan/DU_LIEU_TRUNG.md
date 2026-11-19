# Tạm bỏ qua nội dung trùng và ghi báo cáo

Chức năng áp dụng khi chuẩn bị tập **Pretrain mới** từ tài liệu. Chương trình chỉ lọc bản dữ liệu trong bộ nhớ; không chỉnh sửa hoặc xóa file nguồn.

## Cách hoạt động

1. File có nội dung hoàn toàn giống nhau sau chuẩn hóa Unicode và khoảng trắng: giữ một bản, ghi những file còn lại vào báo cáo.
2. Khi chọn **3 / init-from**, đối chiếu tài liệu trong `Da_Hoc`. Toàn file hoặc dòng dài đã có ở đó được bỏ qua trước khi chia tập dữ liệu.
3. Chia phần còn lại thành train và validation. Dòng trùng với validation bị bỏ khỏi train để tránh học trên nội dung dùng kiểm tra.
4. Trong train, nếu một dòng dài xuất hiện nhiều lần trong cùng file hoặc nhiều file, giữ lần đầu và tạm bỏ qua các lần sau.
5. Chỉ dùng phần còn lại để chuẩn bị dữ liệu huấn luyện. Nếu không còn nội dung mới hoặc không đủ dữ liệu độc lập cho train/validation, chương trình dừng và vẫn xuất báo cáo.

So khớp từng dòng áp dụng với dòng có **ít nhất 80 ký tự** sau chuẩn hóa khoảng trắng. Dòng ngắn như tiêu đề hoặc nhãn được giữ để tránh làm mất cấu trúc tài liệu. So khớp toàn file không có ngưỡng này. Đây là nhận diện trùng chính xác sau chuẩn hóa, không phát hiện mọi câu diễn đạt khác nhau nhưng cùng ý nghĩa, đoạn khác cách xuống dòng, hoặc nội dung mô hình đã biết từ nguồn khác.

`Da_Hoc` chỉ được đọc để đối chiếu, không được tự đưa vào tập train. Nội dung ở đó là tài liệu đã dùng trong phiên trước, không bảo đảm đã có trong trọng số của mọi checkpoint bạn chọn. Chế độ **2 / tạo mô hình mới** không loại theo `Da_Hoc`, vì mô hình mới cần học lại dữ liệu từ đầu. Resume vẫn dùng tập dữ liệu trong checkpoint; không lọc lại dữ liệu cũ.

## Vị trí báo cáo Markdown

Mỗi lần chuẩn bị dữ liệu có một file riêng:

```text
Ket_Qua/Du_Lieu_Da_Xu_Ly/TEN_LAN_HUAN_LUYEN/Du_lieu_trung.md
```

Đường dẫn được in trên màn hình cả khi chuẩn bị thành công lẫn khi phải dừng vì thiếu dữ liệu. Báo cáo ghi:

- Loại trùng và lý do tạm bỏ qua.
- File nguồn bị bỏ qua và file/đoạn được dùng để đối chiếu.
- Nội dung đầy đủ của dòng trùng, số lần và vị trí xuất hiện.
- Mã kiểm tra nội dung. Với toàn file trùng, báo cáo ghi đường dẫn và mã kiểm tra, không chép lại cả file.

Số dòng trong báo cáo là số dòng của **văn bản trích xuất hoặc phần train/validation đang xét**, không phải số bản ghi CSV hay số ô Excel. Dùng chuỗi nội dung trong báo cáo để tìm trong file gốc. Các lần lặp cùng nội dung và cùng nguồn đối chiếu được gộp thành một mục; số mục có thể nhỏ hơn số lượt bỏ qua.

Báo cáo cho dữ liệu đang có đã được tạo tại [Du_lieu_trung_20261118.md](../Ket_Qua/Danh_Gia/Du_lieu_trung_20261118.md). Đây là kiểm tra dữ liệu, chưa chạy huấn luyện.

## Quan hệ với Da_Hoc

File bị bỏ qua hoàn toàn không được coi là nguồn của tập học mới và không tự chuyển sang `Da_Hoc`. File còn nội dung mới thực sự dùng trong tập train/validation vẫn có thể được chuyển nguyên bản sau khi phiên hoàn tất, theo [điều kiện chuyển file](DA_HOC.md). Báo cáo ghi rõ phần nào đã bị bỏ qua; tên `Da_Hoc` không có nghĩa mọi dòng trong file đã được học.

Các cặp hỏi/đáp JSON ở Chat_SFT vẫn theo quy trình duyệt và loại cặp trùng hiện có; chức năng báo cáo dòng văn bản này dành cho Pretrain.
