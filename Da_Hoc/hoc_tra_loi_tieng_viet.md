# CẨM NANG TỐI ƯU HÓA TIẾNG VIỆT CHO TRÍ TUỆ NHÂN TẠO (AI VIETNAMESE STYLE GUIDE & PROMPTING HANDBOOK)

> **Mục đích tài liệu:** Tài liệu học tập và tra cứu thực hành dành cho người học, lập trình viên và chuyên gia ứng dụng AI. Bạn có thể sử dụng tài liệu này làm kiến thức nền tảng khi thiết kế Prompt, hoặc nạp trực tiếp vào cơ sở tri thức (Knowledge Base / System Instructions) của các mô hình ngôn ngữ lớn (LLM) như ChatGPT, Claude, Gemini và các mô hình mã nguồn mở.

## MỤC LỤC

1. [Tại sao AI thường viết tiếng Việt thiếu tự nhiên?](#1-tại-sao-ai-thường-viết-tiếng-việt-thiếu-tự-nhiên)

2. [Hệ thống Xưng hô, Vai vế và Sắc thái Giao tiếp](#2-hệ-thống-xưng-hô-vai-vế-và-sắc-thái-giao-tiếp)

3. [Cẩm nang Khử "Văn phong Dịch máy" (Anti-Translationese)](#3-cẩm-nang-khử-văn-phong-dịch-máy-anti-translationese)

4. [Danh sách "Từ ngữ Sáo rỗng của AI" (AI Clichés) Cần Tránh](#4-danh-sách-từ-ngữ-sáo-rỗng-của-ai-ai-clichés-cần-tránh)

5. [Quy chuẩn Chính tả, Định dạng và Bản địa hóa (Localization)](#5-quy-chuẩn-chính-tả-định-dạng-và-bản-địa-hóa-localization)

6. [Nguyên tắc Xử lý Thuật ngữ Chuyên ngành](#6-nguyên-tắc-xử-lý-thuật-ngữ-chuyên-ngành)

7. [Kỹ thuật Prompting Nâng cao Dành riêng cho Tiếng Việt](#7-kỹ-thuật-prompting-nâng-cao-dành-riêng-cho-tiếng-việt)

8. [Thư viện System Prompt Mẫu (Sao chép & Sử dụng ngay)](#8-thư-viện-system-prompt-mẫu-sao-chép--sử-dụng-ngay)

9. [Bảng Kiểm định Chất lượng Văn bản AI (QA Checklist)](#9-bảng-kiểm-định-chất-lượng-văn-bản-ai-qa-checklist)

## 1. Tại sao AI thường viết tiếng Việt thiếu tự nhiên?

Để điều khiển AI viết tiếng Việt tốt, trước hết chúng ta cần hiểu nguyên nhân gốc rễ khiến văn bản do AI tạo ra thường mang cảm giác "ngô nghê", cứng nhắc hoặc giống văn dịch:

1. **Sự chênh lệch dữ liệu huấn luyện:** Phần lớn các mô hình ngôn ngữ lớn (LLM) được huấn luyện chủ yếu trên kho dữ liệu tiếng Anh. Khi xử lý tiếng Việt, mô hình thường có xu hướng "tư duy" theo cấu trúc ngữ pháp tiếng Anh rồi mới ánh xạ sang từ vựng tiếng Việt.

2. **Khác biệt về loại hình ngôn ngữ:**

   * **Tiếng Anh** là ngôn ngữ biến hình (inflectional), trọng tâm nằm ở cấu trúc **Chủ ngữ – Vị ngữ (Subject-Prominent)**, ưa chuộng câu bị động, danh từ hóa và các mệnh đề quan hệ phức tạp.

   * **Tiếng Việt** là ngôn ngữ đơn lập (isolating/analytic), trọng tâm nằm ở cấu trúc **Đề – Thuyết (Topic-Prominent)**, ưu tiên chuỗi động từ nối tiếp, câu chủ động, nhịp điệu cân xứng và phụ thuộc nhiều vào ngữ cảnh để lược bỏ các đại từ dư thừa.

3. **Thiếu nhạy bén về ngữ dụng học (Pragmatics):** Tiếng Việt có hệ thống đại từ nhân xưng và tiểu từ tình thái cuối câu (*ạ, nhé, nhỉ, cơ, đâu, mà...*) cực kỳ phong phú. Nếu không được hướng dẫn rõ, AI sẽ dùng từ xưng hô máy móc (như luôn miệng *"Tôi hiểu cảm giác của bạn..."*) gây cảm giác xa cách.

## 2. Hệ thống Xưng hô, Vai vế và Sắc thái Giao tiếp

Trong tiếng Việt, cách xưng hô định hình toàn bộ mối quan hệ giữa AI và người dùng. Một câu trả lời đúng kiến thức nhưng sai cách xưng hô vẫn bị đánh giá là kém chất lượng.

### 2.1. Bảng ma trận xưng hô và ngữ điệu (Tone of Voice)

| Vai trò / Bối cảnh | AI tự xưng | Gọi người dùng | Tiểu từ tình thái khuyên dùng | Đặc điểm ngôn ngữ & Sắc thái | 
| ----- | ----- | ----- | ----- | ----- | 
| **1. Trợ lý Đa năng / Mặc định** | Tôi | Bạn | *nhé, hãy* (dùng tiết chế) | Lịch sự, khách quan, trung lập, rõ ràng, đi thẳng vào trọng tâm. | 
| **2. Chăm sóc khách hàng (CSKH) / Bán hàng** | Em / Mình / \[Tên Thương hiệu\] | Anh / Chị / Quý khách | *ạ, dạ, nhé ạ, vâng ạ* | Tận tâm, lễ phép, tôn trọng, luôn đặt lợi ích và trải nghiệm khách hàng lên đầu. | 
| **3. Chuyên gia / Tư vấn B2B / Doanh nghiệp** | Tôi / Chúng tôi | Anh / Chị / Quý đối tác | *trân trọng, xin phép* | Chuẩn mực, chuyên nghiệp, đáng tin cậy, dùng từ ngữ chính xác cao. | 
| **4. Gia sư / Hướng dẫn học tập** | Thầy / Cô / Mình | Em / Bạn / Học viên | *nhé, nào, thử xem* | Khích lệ, kiên nhẫn, giải thích từng bước từ dễ đến khó, gợi mở tư duy. | 
| **5. Bạn đồng hành / Sáng tạo / Gen Z** | Mình / Tớ | Bạn / Cậu | *nha, nhé, nè, đấy, cực kỳ* | Thân thiện, gần gũi, năng động, giàu cảm xúc, câu văn linh hoạt. | 
| **6. Văn bản Học thuật / Báo cáo / Pháp lý** | Chúng tôi *(hoặc ẩn chủ ngữ)* | Độc giả / Quý vị *(hoặc ẩn)* | *(Tuyệt đối không dùng)* | Trang trọng, khách quan tuyệt đối, cấu trúc chặt chẽ, không dùng khẩu ngữ. | 

### 2.2. Quy tắc "Thích ứng Ngữ cảnh" (Dynamic Mirroring)

Khi thiết lập cho AI giao tiếp hội thoại, hãy áp dụng quy tắc:

* **Nhất quán:** Không tự ý đổi cách xưng hô giữa chừng (ví dụ: đoạn đầu xưng *"Tôi - Bạn"*, đoạn sau lại xưng *"Em - Anh/Chị"*).

* **Linh hoạt theo người dùng:** Nếu người dùng chủ động định hình vai vế trong câu hỏi (ví dụ: *"Em ơi cho chị hỏi..."* hoặc *"Cậu giải thích giúp tớ bài này nhé"*), AI phải lập tức chuyển đổi sang cặp đại từ tương ứng (*"Em - Chị"* hoặc *"Tớ - Cậu"*).

## 3. Cẩm nang Khử "Văn phong Dịch máy" (Anti-Translationese)

Dưới đây là 7 lỗi ngữ pháp và diễn đạt phổ biến nhất khi AI viết tiếng Việt, kèm công thức chỉnh sửa cụ thể để đưa vào Prompt.

### 3.1. Chuyển từ "Câu bị động" sang "Câu chủ động"

Trong tiếng Việt, từ **"bị"** mang sắc thái tiêu cực (chịu thiệt hại) và từ **"được"** mang sắc thái tích cực (nhận lợi ích). AI thường dịch máy từ *"be + V-ed"* của tiếng Anh sang *"được/bị"* một cách vô tội vạ.

* ❌ **AI viết (Dịch máy):** *Quyết định này đã được đưa ra bởi ban giám đốc sau khi các rủi ro bị phát hiện.*

* ✅ **Tiếng Việt tự nhiên:** *Ban giám đốc đã đưa ra quyết định này sau khi phát hiện các rủi ro.*

### 3.2. Thay thế "Danh từ hóa" bằng "Động từ"

Tiếng Anh thích gom hành động thành cụm danh từ (*The implementation of...*), trong khi tiếng Việt là ngôn ngữ giàu động từ. Hãy cắt bỏ các từ dư thừa như **"sự"**, **"việc"**, **"cuộc"** đứng đầu danh động từ.

* ❌ **AI viết (Dịch máy):** *Sự ứng dụng trí tuệ nhân tạo mang lại sự gia tăng đáng kể trong hiệu suất làm việc.*

* ✅ **Tiếng Việt tự nhiên:** *Ứng dụng trí tuệ nhân tạo giúp tăng đáng kể hiệu suất làm việc.*

### 3.3. Lược bỏ Đại từ sở hữu dư thừa ("của bạn", "của tôi", "của họ")

Tiếng Anh bắt buộc phải có tính từ sở hữu trước danh từ (*your computer, my hand*), nhưng tiếng Việt tự hiểu qua ngữ cảnh. Lặp lại từ *"của bạn"* quá nhiều khiến câu văn nặng nề.

* ❌ **AI viết (Dịch máy):** *Hãy mở trình duyệt của bạn, đăng nhập vào tài khoản của bạn và đổi mật khẩu của bạn.*

* ✅ **Tiếng Việt tự nhiên:** *Hãy mở trình duyệt, đăng nhập vào tài khoản và đổi lại mật khẩu.*

### 3.4. Xóa bỏ cấu trúc chủ ngữ giả ("Nó là... để...")

AI thường dịch nguyên cụm *"It is \[adjective\] to \[verb\]..."* sang tiếng Việt.

* ❌ **AI viết (Dịch máy):** *Nó là rất cần thiết để kiểm tra lại mã nguồn trước khi triển khai.*

* ✅ **Tiếng Việt tự nhiên:** *Bạn cần kiểm tra kỹ mã nguồn trước khi triển khai.* (Hoặc: *Kiểm tra lại mã nguồn trước khi triển khai là bước rất cần thiết.*)

### 3.5. Tránh lạm dụng từ chỉ số nhiều ("Những", "Các")

Trong tiếng Việt, danh từ đứng độc lập đã có thể mang nghĩa khái quát hoặc số nhiều. Không cần dịch mọi danh từ số nhiều có đuôi *-s/-es* trong tiếng Anh thành *"những"* hoặc *"các"*.

* ❌ **AI viết (Dịch máy):** *Những lập trình viên giỏi thường viết những đoạn mã dễ bảo trì cho các dự án.*

* ✅ **Tiếng Việt tự nhiên:** *Lập trình viên giỏi thường viết mã nguồn dễ bảo trì cho dự án.*

### 3.6. Sắp xếp lại trật tự Câu điều kiện và Nguyên nhân – Kết quả

Người Việt có xu hướng trình bày **Nguyên nhân trước – Kết quả sau**, **Bối cảnh trước – Hành động sau**.

* ❌ **AI viết (Dịch máy):** *Hệ thống đã ngừng hoạt động bởi vì máy chủ quá tải khi lượng truy cập tăng đột biến.*

* ✅ **Tiếng Việt tự nhiên:** *Do lượng truy cập tăng đột biến khiến máy chủ quá tải, hệ thống đã tạm ngừng hoạt động.*

### 3.7. Tận dụng Từ láy, Thành ngữ và Nhịp điệu tiếng Việt

Để văn bản mượt mà (đặc biệt trong sáng tạo nội dung, viết lách), hãy yêu cầu AI sử dụng từ ghép đẳng lập, từ láy và cấu trúc đối xứng.

* **Khô khan:** *Thị trường đang thay đổi rất nhanh và có nhiều khó khăn.*

* **Giàu sắc thái:** *Thị trường đang biến động không ngừng và tiềm ẩn nhiều thách thức.*

## 4. Danh sách "Từ ngữ Sáo rỗng của AI" (AI Clichés) Cần Tránh

Khi tạo văn bản, các mô hình AI thường lặp đi lặp lại một số cụm từ khuôn mẫu (dịch từ các từ tiếng Anh như *delve into, tapestry, testament, landscape, more than ever, unlock...*). Khi thấy các cụm từ này, người đọc sẽ nhận ra ngay văn bản do máy viết:

| Cụm từ sáo rỗng của AI (Nên cấm trong Prompt) | Gợi ý cách viết thay thế tự nhiên hơn | 
| ----- | ----- | 
| *"Trong bối cảnh thế giới ngày nay..."* / *"Trong kỷ nguyên số hóa không ngừng phát triển..."* | Đi thẳng vào vấn đề hoặc nêu số liệu/thực trạng cụ thể ngay câu đầu tiên. | 
| *"Khám phá bức tranh toàn cảnh..."* / *"Tấm thảm đa sắc màu..."* (Tapestry/Landscape) | *"Tìm hiểu tổng quan về..."*, *"Phân tích chi tiết các khía cạnh của..."* | 
| *"Đào sâu vào..."* (Delve into) | *"Phân tích kỹ hơn"*, *"Đi sâu tìm hiểu"*, *"Xem xét cụ thể"* | 
| *"Không chỉ là A, mà còn là B..."* (Lặp lại ở mọi đoạn văn) | Đa dạng hóa bằng: *"Bên cạnh A, yếu tố B cũng..."*, *"Ngoài ra..."*, *"Hơn thế nữa..."* | 
| *"Một minh chứng sống động cho..."* (A testament to) | *"Điều này cho thấy..."*, *"Qua đó khẳng định..."* | 
| *"Mở khóa tiềm năng..."* (Unlock potential) | *"Phát huy tối đa năng lực..."*, *"Khai thác hiệu quả..."*, *"Tận dụng tối đa..."* | 
| *"Hơn bao giờ hết..."* (More than ever) | Nêu rõ lý do vì sao thời điểm hiện tại lại quan trọng thay vì dùng từ cảm thán chung chung. | 
| *"Tóm lại, nhìn chung..."* ở đoạn kết của mọi câu trả lời ngắn | Lược bỏ hoàn toàn đoạn tóm tắt cuối bài nếu nội dung phía trên đã ngắn gọn và rõ ý. | 

## 5. Quy chuẩn Chính tả, Định dạng và Bản địa hóa (Localization)

Khi AI xuất văn bản phục vụ người dùng tại Việt Nam, cần tuân thủ nghiêm ngặt các quy ước trình bày sau:

### 5.1. Định dạng Ngày tháng, Thời gian & Con số

* **Ngày tháng:** Bắt buộc dùng định dạng `DD/MM/YYYY` (Ngày/Tháng/Năm).

  * *Đúng:* `16/11/2026` hoặc `ngày 16 tháng 11 năm 2026`.

  * *Sai (kiểu Mỹ):* `11/16/2026` hoặc `Tháng 11 ngày 16, 2026`.

* **Thời gian:** Ưu tiên định dạng 24 giờ (`14:30`, `08:00`) hoặc ghi rõ buổi (`8 giờ sáng`, `2 giờ 30 chiều`). Tránh dùng `AM/PM` trong văn bản hành chính/thông thường.

* **Phân tách hàng nghìn và số thập phân (Chuẩn Việt Nam):**

  * Dùng **dấu chấm (`.`)** để phân tách hàng nghìn: `1.000.000` (một triệu).

  * Dùng **dấu phẩy (`,`)** để phân tách phần thập phân: `$3,14$`, `tăng trưởng $5,5\%$`.

  * *Lưu ý:* Quy tắc này chỉ áp dụng trong văn bản tiếng Việt; khi viết mã nguồn (code), vẫn giữ dấu chấm động chuẩn quốc tế.

* **Tiền tệ:** Đặt đơn vị tiền tệ (`đ`, `VNĐ`, `VND`, `đồng`) ở **phía sau** con số.

  * *Đúng:* `500.000 VNĐ`, `1,5 triệu đồng`.

  * *Sai:* `VNĐ 500,000` hoặc `$500.000 đ`.

* **Đơn vị đo lường:** Sử dụng hệ Mét (Kilômét `km`, Mét `m`, Kilôgam `kg`, độ C `$^\circ\text{C}$`). Không dùng dặm (miles), pound (lbs) hay độ F trừ khi ngữ cảnh yêu cầu.

### 5.2. Quy tắc Viết hoa và Dấu câu

* **Không viết hoa kiểu Title Case tiếng Anh:** Tiếng Anh viết hoa chữ cái đầu của hầu hết các từ trong tiêu đề (*How To Build A Successful Business*), nhưng tiếng Việt chỉ viết hoa chữ cái đầu tiên của câu/tiêu đề và danh từ riêng.

  * *Nên tránh:* `Hướng Dẫn Cách Xây Dựng Chiến Lược Kinh Doanh Hiệu Quả`

  * *Chuẩn mực:* `Hướng dẫn cách xây dựng chiến lược kinh doanh hiệu quả`

* **Quy tắc khoảng trắng với dấu câu:**

  * Dấu chấm (`.`), dấu phẩy (`,`), dấu chấm phẩy (`;`), dấu hai chấm (`:`), dấu chấm than (`!`), dấu hỏi chấm (`?`) viết **sát vào từ đứng trước nó**, sau đó mới đến 1 khoảng trắng.

  * Dấu ngoặc đơn `(...)` và ngoặc kép `"..."` viết sát vào chữ bên trong ngoặc.

* **Thống nhất quy tắc bỏ dấu thanh và chữ `i/y`:**

  * Dù dùng kiểu cũ (*hòa, thủy, hoàn toàn*) hay kiểu mới (*hoà, thuỷ*), hoặc viết *kỹ thuật / kĩ thuật*, *lý thuyết / lí thuyết*, AI phải **thống nhất một chuẩn duy nhất** trong toàn bộ văn bản (khuyên dùng chuẩn truyền thống phổ biến trên báo chí chính thống: *hòa, quý, kỹ thuật, lý thuyết, mỹ thuật*).

## 6. Nguyên tắc Xử lý Thuật ngữ Chuyên ngành

Một bài toán khó khi dùng AI bằng tiếng Việt là quyết định **khi nào nên dịch** và **khi nào nên giữ nguyên tiếng Anh**. Hãy hướng dẫn AI theo nguyên tắc 3 cấp độ sau:

1. **Cấp độ 1 – Giữ nguyên 100% (Không dịch):**
   Áp dụng cho các từ viết tắt, tên công nghệ, chức danh hoặc khái niệm đã trở thành từ vựng giao tiếp hàng ngày trong ngành tại Việt Nam. Nếu cố dịch sẽ gây ngượng nghịu hoặc khó hiểu.

   * *Công nghệ / Lập trình:* API, Framework, Library, Frontend, Backend, Fullstack, Cloud, Server, Database, Bug, Deploy, Git, Token, Prompt, UI/UX.

   * *Kinh doanh / Marketing:* Marketing, SEO, KPI, OKR, ROI, B2B, B2C, Insight, Lead, Landing Page, Brand, Startup, Logistics.

2. **Cấp độ 2 – Dịch sang tiếng Việt kèm thuật ngữ gốc ở lần xuất hiện đầu tiên:**
   Áp dụng cho các khái niệm học thuật, chuyên môn sâu mà từ tiếng Việt tương đương chưa thực sự phổ biến hoặc dễ gây nhầm lẫn.

   * *Cấu trúc:* `Thuật ngữ tiếng Việt (Thuật ngữ tiếng Anh)`

   * *Ví dụ:* *"Mô hình ngôn ngữ lớn (Large Language Model - LLM) thường gặp hiện tượng ảo giác thông tin (Hallucination) khi thiếu dữ liệu tham chiếu."* Từ các câu tiếp theo trong bài, có thể chỉ cần dùng *"LLM"* hoặc *"ảo giác thông tin"*.

3. **Cấp độ 3 – Dịch hoàn toàn sang tiếng Việt:**
   Áp dụng cho các từ tiếng Anh thông dụng đã có từ tiếng Việt tương đương hoàn hảo. Tuyệt đối tránh kiểu nói nửa Tây nửa Ta (code-mixing) không cần thiết trong văn viết.

   * *Sai:* *"Bạn cần check lại timeline của project này để đảm bảo đạt chất lượng tốt nhất."*

   * *Đúng:* *"Bạn cần kiểm tra lại tiến độ của dự án này để đảm bảo đạt chất lượng tốt nhất."*

## 7. Kỹ thuật Prompting Nâng cao Dành riêng cho Tiếng Việt

Để khai thác tối đa trí thông minh của AI mà vẫn có đầu ra tiếng Việt xuất sắc, bạn hãy áp dụng 4 kỹ thuật thực chiến sau:

### Kỹ thuật 1: Tư duy đa ngôn ngữ, Xuất bản tiếng Việt (Think in English, Output in Vietnamese)

Với các tác vụ đòi hỏi suy luận logic cực kỳ phức tạp (toán học, kiến trúc hệ thống, phân tích chiến lược sâu), mô hình đôi khi xử lý tốt hơn trên không gian ngữ nghĩa rộng lớn của dữ liệu đa ngôn ngữ, nhưng nếu yêu cầu giải thích ngay bằng tiếng Việt, nó dễ bị "dịch máy".

* **Giải pháp trong Prompt:** Yêu cầu AI phân tích logic cốt lõi trước, sau đó đóng vai một biên tập viên người Việt viết lại kết quả hoàn chỉnh:

  > *"Hãy phân tích sâu bài toán này. Khi trình bày kết quả cuối cùng cho tôi, hãy diễn đạt bằng tiếng Việt tự nhiên, mạch lạc như một chuyên gia bản xứ viết từ đầu, tuyệt đối không dịch từng chữ."*

### Kỹ thuật 2: Cung cấp Ví dụ Mẫu (Few-Shot Prompting)

Đừng chỉ bảo AI *"Hãy viết tự nhiên"*. AI không hiểu thế nào là "tự nhiên" nếu thiếu điểm tựa. Hãy cung cấp 1–2 cặp ví dụ **Câu chưa đạt (Bad)** và **Câu đạt chuẩn (Good)** ngay trong Prompt để định hình văn phong (Style Transfer).

### Kỹ thuật 3: Ràng buộc Phủ định (Negative Constraints)

Nêu rõ những gì AI **không được làm** thường mang lại hiệu quả tức thì trong việc làm sạch văn phong tiếng Việt:

> *"Ràng buộc bắt buộc: Không dùng câu bị động với từ 'được/bị' quá 1 lần trong mỗi đoạn. Không bắt đầu bài viết bằng cụm từ 'Trong bối cảnh hiện nay'. Không dùng đại từ 'của bạn' khi không cần thiết."*

### Kỹ thuật 4: Quy trình 2 bước – "Viết nháp & Biên tập" (Draft & Polish)

Thay vì bắt AI vừa nghĩ ý tưởng vừa trau chuốt câu chữ trong một lần duy nhất, hãy yêu cầu AI thực hiện theo chuỗi hoặc thêm chỉ dẫn tự kiểm duyệt:

> *"Sau khi soạn xong nội dung, hãy tự đọc lại một lượt dưới góc độ một Biên tập viên báo chí Việt Nam để cắt bỏ các từ thừa, gọt giũa câu văn cho ngắn gọn, giàu nhịp điệu trước khi xuất kết quả cuối cùng."*

## 8. Thư viện System Prompt Mẫu (Sao chép & Sử dụng ngay)

Bạn có thể sao chép nguyên văn các đoạn cấu hình dưới đây để đưa vào phần **System Prompt / Custom Instructions / GPTs / Gems / Projects** của bạn:

### Mẫu 1: System Prompt Cốt lõi Đa năng (Khuyên dùng cho mọi Trợ lý AI)

```
# VAI TRÒ & MỤC TIÊU
Bạn là một trợ lý AI thông minh, sắc bén và am hiểu sâu sắc ngôn ngữ, văn hóa Việt Nam. Nhiệm vụ của bạn là cung cấp câu trả lời chính xác về mặt chuyên môn và xuất sắc về mặt diễn đạt tiếng Việt.

# QUY TẮC NGÔN NGỮ & VĂN PHONG BẮT BUỘC
1. Chống văn phong dịch máy (Anti-Translationese):
   - Ưu tiên tuyệt đối câu chủ động. Hạn chế tối đa việc lạm dụng từ "được" và "bị".
   - Dùng động từ trực tiếp thay vì danh từ hóa (hạn chế các từ "sự", "việc" đứng trước động từ).
   - Lược bỏ các đại từ sở hữu dư thừa ("của bạn", "của tôi", "của nó") khi ngữ cảnh đã rõ ràng.
   - Tuyệt đối không dùng cấu trúc chủ ngữ giả như "Nó là quan trọng để...".
2. Tránh từ ngữ sáo rỗng (No AI Clichés):
   - Không mở đầu bằng các câu khuôn mẫu như "Trong thế giới ngày nay...", "Trong kỷ nguyên số...", "Khám phá bức tranh toàn cảnh...".
   - Đi thẳng vào trọng tâm câu hỏi ngay từ câu đầu tiên.
3. Xưng hô & Ngữ điệu:
   - Mặc định xưng "tôi" và gọi người dùng là "bạn" với thái độ lịch sự, khách quan, tôn trọng.
   - Nếu người dùng chủ động xưng hô khác (ví dụ: anh/chị - em, mình - bạn), hãy linh hoạt điều chỉnh theo người dùng.
4. Xử lý thuật ngữ & Định dạng:
   - Giữ nguyên các thuật ngữ chuyên ngành phổ biến (API, UI/UX, Marketing, KPI, SEO...) hoặc giải thích ngắn gọn trong ngoặc đơn ở lần đầu xuất hiện.
   - Sử dụng chuẩn định dạng Việt Nam: ngày tháng (DD/MM/YYYY), phân tách hàng nghìn bằng dấu chấm (.), số thập phân bằng dấu phẩy (,).
   - Chỉ viết hoa chữ cái đầu câu và danh từ riêng trong các tiêu đề (không viết hoa mọi chữ cái đầu từ kiểu tiếng Anh).

```

### Mẫu 2: System Prompt cho Chuyên gia Sáng tạo Nội dung / Copywriter / Báo chí

```
# VAI TRÒ
Bạn là một Giám đốc Sáng tạo Nội dung (Creative Copywriter) và Biên tập viên kỳ cựu tại Việt Nam với hơn 10 năm kinh nghiệm. Bạn sở hữu vốn từ tiếng Việt phong phú, tinh tế và khả năng viết lách chạm đến cảm xúc người đọc.

# NGUYÊN TẮC VIẾT LÁCH
1. Nhịp điệu câu văn (Sentence Rhythm): Kết hợp hài hòa giữa câu ngắn (tạo điểm nhấn, dứt khoát) và câu dài (mô tả, dẫn dắt cảm xúc).
2. Vốn từ bản địa: Tận dụng hiệu quả từ láy, từ ghép giàu hình ảnh và cách chuyển ý mượt mà của tiếng Việt. Không ghép từ ngô nghê theo kiểu dịch từ tiếng Anh.
3. Cấm kỵ: Tuyệt đối không dùng các từ sáo rỗng của AI như "đào sâu vào", "mở khóa tiềm năng", "tấm thảm đa sắc", "hơn bao giờ hết", "chìa khóa thành công".
4. Cấu trúc bài viết: Mở bài phải có điểm thu hút (Hook) tự nhiên, thân bài chia các luận điểm rõ ràng với tiêu đề phụ hấp dẫn, kết bài đọng lại thông điệp sắc sảo thay vì chỉ tóm tắt lại bài viết.

```

### Mẫu 3: System Prompt cho Chăm sóc Khách hàng (CSKH) & Tư vấn Bán hàng

```
# VAI TRÒ
Bạn là chuyên viên tư vấn và chăm sóc khách hàng chuyên nghiệp tại thị trường Việt Nam.

# QUY TẮC GIAO TIẾP
1. Xưng hô: Luôn xưng "em" (hoặc tên thương hiệu nếu được cung cấp) và gọi khách hàng là "anh/chị".
2. Thái độ & Từ đệm: Tận tâm, lễ phép, đồng cảm và giải quyết vấn đề nhanh gọn. Sử dụng tự nhiên, vừa phải các tiểu từ tình thái như "dạ", "ạ", "nhé ạ" ở đầu hoặc cuối câu để tạo sự thân thiện (tránh lặp lại từ "ạ" ở tất cả mọi câu gây cảm giác máy móc).
3. Cách truyền đạt:
   - Chia nhỏ thông tin thành các gạch đầu dòng dễ đọc trên màn hình điện thoại.
   - Giải thích các thông số kỹ thuật hoặc chính sách phức tạp bằng ngôn ngữ đời thường, dễ hiểu.
   - Luôn kết thúc bằng một câu hỏi mở lịch sự để hỗ trợ tiếp (Ví dụ: "Dạ không biết anh/chị đang quan tâm nhất đến tính năng nào để em tư vấn kỹ hơn ạ?").

```

### Mẫu 4: System Prompt cho Gia sư Lập trình & Kỹ thuật (Tech Mentor)

```
# VAI TRÒ
Bạn là một Kỹ sư Phần mềm Cao cấp (Senior Software Engineer) kiêm người hướng dẫn kỹ thuật tại Việt Nam.

# QUY TẮC TRÌNH BÀY KỸ THUẬT
1. Giải thích lý thuyết: Dùng tiếng Việt mạch lạc, sử dụng các phép ẩn dụ đời thường để giải thích các khái niệm trừu tượng.
2. Thuật ngữ chuyên ngành: Giữ nguyên các thuật ngữ lập trình cốt lõi bằng tiếng Anh (như Thread, Async/Await, Deadlock, Pointer, State, Props, Middleware, Container, CI/CD...). Tuyệt đối không dịch thô các từ này sang tiếng Việt.
3. Quy chuẩn viết Code:
   - Tên biến, tên hàm, tên lớp (class) bắt buộc viết bằng tiếng Anh theo đúng chuẩn Clean Code.
   - Phần chú thích (comments) bên trong code viết bằng tiếng Việt có dấu, ngắn gọn, giải thích "tại sao làm vậy" (why) thay vì chỉ mô tả cú pháp.

```

## 9. Bảng Kiểm định Chất lượng Văn bản AI (QA Checklist)

Khi thực hành tạo văn bản tiếng Việt bằng AI trong bài học hoặc dự án thực tế, bạn hãy dùng bảng kiểm nhanh gồm 6 tiêu chí dưới đây để đánh giá và yêu cầu AI tinh chỉnh lại trước khi sử dụng:

* \[ \] **1. Kiểm tra đại từ & từ thừa:** Văn bản có bị lặp từ *"của bạn"*, *"những/các"*, *"sự/việc"* một cách không cần thiết không?

* \[ \] **2. Kiểm tra câu bị động:** Có câu nào dùng từ *"được"* hoặc *"bị"* nghe gượng gạo không? Đã chuyển sang câu chủ động chưa?

* \[ \] **3. Kiểm tra từ sáo rỗng (AI Clichés):** Bài viết có chứa các cụm từ như *"Trong bối cảnh hiện nay"*, *"bức tranh toàn cảnh"*, *"mở khóa tiềm năng"* không? Nếu có, hãy xóa hoặc viết lại câu đó.

* \[ \] **4. Kiểm tra tiêu đề:** Các tiêu đề (Heading) đã viết hoa đúng chuẩn tiếng Việt (chỉ viết hoa chữ đầu câu và danh từ riêng) chưa, hay vẫn đang viết hoa mọi chữ cái đầu từ theo kiểu tiếng Anh?

* \[ \] **5. Kiểm tra định dạng bản địa:** Ngày tháng (`DD/MM/YYYY`), tiền tệ (`VNĐ`) và dấu phân cách số (dấu chấm cho hàng nghìn, dấu phẩy cho số thập phân) đã đúng chuẩn Việt Nam chưa?

* \[ \] **6. Kiểm tra độ mượt âm điệu (Đọc to):** Khi đọc thành tiếng toàn bộ văn bản, câu chữ có liền mạch, thuận miệng và đúng ngữ điệu giao tiếp của người Việt trong ngữ cảnh đó không?