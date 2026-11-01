# FixCare — Demo readiness

Kiểm tra ngày 27/10/2026. Kết luận: **môi trường chạy được, chưa đủ dữ liệu để demo ghi nghiệp vụ xuyên suốt PostgreSQL**. Không tự seed/reset, không sửa .env, không tạo lịch hay giao dịch thật để kiểm thử.

### Chốt lần cuối ngày 27/10/2026

- Hai hotfix đã commit cục bộ: `1386e20` — `fix(repairs): enforce intake assignment and handle missing technician phone`. Commit chỉ có hai service và hai file test Backend liên quan; không có môi trường, cache, auth state hay ZIP.
- Chạy lại tối thiểu: Backend **35/35 PASS**, Ruff lint/format PASS; Playwright kiểm tra khách duyệt báo giá và đọc thông báo **1/1 PASS** bằng mock, không chạy lại toàn bộ 51 case. Đây là kết quả lượt final preparation; số liệu 58/22 ở mục 6 là lượt readiness trước.
- Kiểm tra PostgreSQL bằng transaction READ ONLY vẫn cho kết quả: dịch vụ active, bốn tài khoản role riêng, hồ sơ technician liên kết và ca AVAILABLE đều **0**. Chưa thể nghiệm thu demo ghi dữ liệu xuyên suốt.
- Đã đối chiếu quy tắc báo giá với DOCX; kết luận và giới hạn ở mục 4.1. Checklist để bạn thao tác ở mục 9.

## 1. Điều kiện thực tế

| Điều kiện | Kết quả | Việc cần làm |
|---|---|---|
| FastAPI `127.0.0.1:8000` | PASS, OpenAPI HTTP 200 | Đã nạp lại hai hotfix sau kiểm thử. |
| PostgreSQL Docker | PASS, running/healthy | Không đổi password, volume hoặc schema. |
| Kết nối DB từ cấu hình Backend | PASS, transaction READ ONLY | Chỉ truy vấn số lượng, không commit. |
| Vite `localhost:5173` | PASS, HTTP 200 | Public browser test gọi API catalog thật bằng GET. |
| Schema | 70 path, 93 operation, 0 operationId trùng | Không đổi contract, không cần regenerate client. |
| Dịch vụ active có thời lượng | 0 | Tạo qua `/workspace/services`. |
| Customer active, không superuser | 0 | Tạo qua `/admin` hoặc khách tự đăng ký. |
| Staff active, không superuser | 0 | Tạo qua `/admin`. |
| Technician active, không superuser | 0 | Tạo qua `/admin`. |
| Manager active, không superuser | 0 | Tạo qua `/admin`. |
| Hồ sơ kỹ thuật viên active gắn đúng tài khoản | 0 | Tạo qua `/workspace/technicians`. |
| Ca AVAILABLE hôm nay/tương lai, giờ hợp lệ, gắn kỹ thuật viên trên | 0 | Tạo ca qua `/workspace/technicians`. |
| Tài khoản `role=customer` nhưng `is_superuser=true` | 1 | Giữ nguyên dữ liệu; không dùng tài khoản này để kiểm tra quyền customer. |

Chạy lại kiểm tra an toàn từ thư mục gốc:

```powershell
.venv/Scripts/python.exe -W ignore scripts/check_demo_readiness.py
```

`data_prerequisites_ready=false` có nghĩa thiếu dữ liệu, không phải lỗi kết nối. Script trả exit 0 nếu việc truy vấn hoàn tất, không đồng nghĩa demo đã sẵn sàng. Chỉ in số lượng/trạng thái, không in email, mật khẩu, hash, token hoặc connection string.

## 2. Chuẩn bị qua UI — người dùng tự thực hiện

Chỉ nhập trên database local/test được phép. Đây là hướng dẫn, agent chưa tạo dữ liệu.

1. Đăng nhập superuser hiện có. Mở `/admin` → **Add User**. Tạo riêng bốn tài khoản có vai trò `customer`, `staff`, `technician`, `manager`; chọn **Is active?**, không chọn **Is superuser?**. Dùng email phân biệt và mật khẩu riêng do bạn tự đặt/lưu an toàn, không ghi vào tài liệu hoặc ZIP.
2. Đăng nhập manager → `/workspace/services`. Nhập dịch vụ minh họa, ví dụ **Thay pin (demo)**, giá tham khảo **100000 VNĐ**, thời lượng **30 phút**, trạng thái **Đang cung cấp** → **Lưu dịch vụ**. Mong đợi: thấy trong danh mục và `/services` công khai. Dữ liệu ví dụ chỉ được lưu khi bạn chủ động nhập UI, không hardcode vào sản phẩm.
3. Manager → `/workspace/technicians`. Nhập tên kỹ thuật viên, số điện thoại nếu có; dropdown **Tài khoản kỹ thuật viên (tùy chọn)** chọn đúng tài khoản technician vừa tạo → **Tạo kỹ thuật viên**. Mong đợi: tài khoản được liên kết, không cần nhập UUID.
4. Chọn hồ sơ kỹ thuật viên → ngày demo (ưu tiên ngày mai), bắt đầu **08:00**, kết thúc **17:00** → **Thêm ca làm việc**. Mong đợi: có ca **AVAILABLE**. Dịch vụ 30 phút phải nằm trọn trong ca; chọn một giờ còn trống do API trả về, không tự đoán giờ.
5. Chạy lại script kiểm tra. Mong đợi: mỗi role ít nhất 1, có dịch vụ/linked technician/ca AVAILABLE. Script chỉ kiểm tra điều kiện tổng quát; vẫn cần kiểm tra slot thực tế cho đúng ngày trên `/booking`.
6. Dùng **bốn profile trình duyệt khác nhau** (ví dụ tạo profile Chrome tên Customer, Staff, Technician, Manager), hoặc các trình duyệt khác nhau. Bốn tab/cửa sổ trong cùng profile không tách phiên; các cửa sổ ẩn danh cùng trình duyệt cũng có thể chia sẻ phiên. Đăng xuất/đăng nhập trong cùng profile có thể đổi tài khoản của tab khác. Không dùng chung superuser để đóng vai cả bốn người.

## 3. Kịch bản demo chính

Ghi lại mã lịch `APPT-...` và mã báo giá/hóa đơn hiển thị sau mỗi bước, không dùng ID hardcode. Trước khi tạo lịch phải đăng nhập customer để lịch gắn với tài khoản và xuất hiện trong “Lịch hẹn của tôi”. Đặt lịch khách vãng lai không đảm bảo có lịch trong tài khoản đăng nhập sau.

| Bước | Vai trò / route | Thao tác | Kết quả mong đợi |
|---:|---|---|---|
| 1 | Customer — `/booking` | Chọn dịch vụ/ngày, để tự phân công hoặc chọn technician, chọn slot thật; nhập tên/điện thoại kiểm thử hợp lệ, hãng/dòng máy. Xem tóm tắt → Xác nhận. | Thành công, có mã lịch; request tạo lịch chỉ gửi một lần khi đang xử lý. |
| 2 | Customer — `/appointments` → link chi tiết | Mở lịch vừa tạo, có thể reload URL `/appointments/<id>`. | Chỉ lịch của mình, đúng dịch vụ/giờ/trạng thái PENDING. |
| 3 | Staff — `/workspace/appointments` | Tìm mã lịch, mở chi tiết → Xác nhận lịch → xác nhận dialog. | CONFIRMED; danh sách và nhật ký cập nhật. |
| 4 | Staff — cùng chi tiết lịch | Nhập Ngoại quan thiết bị, Mô tả lỗi, Phụ kiện → Tiếp nhận thiết bị. | Thông báo thành công, dữ liệu tiếp nhận được lưu. Không dùng form vãng lai để thay thế lịch đã có vì sẽ tạo phiếu khác. |
| 5 | Staff — `/workspace/repairs` | Chọn đúng mã phiếu → Kỹ thuật viên phụ trách → Phân công kỹ thuật viên. | Đúng hồ sơ technician đã liên kết. Dù đặt lịch tự phân công, bước này xác minh lại người chịu trách nhiệm. |
| 6 | Technician — `/workspace/repairs` | Mở phiếu được giao; Trạng thái mới `IN_PROGRESS`, nhập Chẩn đoán kỹ thuật và Ghi chú → Cập nhật tiến độ → xác nhận. | Chẩn đoán được lưu. Hệ thống hiện gộp chẩn đoán và sửa chữa trong IN_PROGRESS, không có trạng thái chẩn đoán riêng. |
| 7 | Technician/Staff — cùng phiếu | Lập báo giá: tên hạng mục, đơn giá, số lượng từng dòng → Tạo báo giá gửi khách. | Báo giá SENT, tổng tiền Backend tính; thêm dòng không mất dữ liệu đã nhập. |
| 8 | Customer — `/quotes` | Chọn đúng mã báo giá, kiểm tra hạng mục/tổng tiền → Duyệt báo giá → xác nhận. | ACCEPTED. Demo dùng customer thực sự duyệt, không dùng staff duyệt hộ. |
| 9 | Technician — `/workspace/repairs` | Sau khi khách duyệt mới sửa; hoàn tất kiểm tra máy → trạng thái COMPLETED, ghi chú kết quả → xác nhận. | Phiếu COMPLETED và có nhật ký hoàn tất. Không gửi IN_PROGRESS lần nữa nếu đã ở trạng thái này. |
| 10 | Staff — `/invoices` | Chọn báo giá ACCEPTED của phiếu COMPLETED → Lập hóa đơn. | Có số hóa đơn, hạng mục và số dư phải thu. |
| 11 | Staff — `/invoices` | Nhập tiền đã nhận, CASH hoặc BANK_TRANSFER → Ghi nhận thanh toán → xác nhận. | PAID nếu đủ; PARTIALLY_PAID nếu còn thiếu. Đây là ghi nhận tại quầy, không chuyển tiền thật qua cổng thanh toán. |
| 12 | Staff — `/invoices` | Khi PAID → Bàn giao thiết bị → xác nhận. | Nhật ký và thông báo bàn giao. Không bàn giao khi còn nợ. |
| 13 | Customer — `/invoices`, `/notifications`, `/reviews` | Xem hóa đơn/khoản thu, đọc thông báo, gửi đánh giá cho lịch COMPLETED. | Chỉ dữ liệu của mình, mỗi phiếu một đánh giá. |
| 14 | Manager — `/workspace/reports` | Chọn khoảng ngày có thanh toán; xem KPI/biểu đồ hoặc xuất CSV. | Doanh thu là tiền SUCCESS đã thu, không phải giá tham khảo/tổng lịch. |

Kịch bản đổi/hủy nên dùng một lịch demo khác được người phụ trách cho phép tạo; không hủy phiếu đang dùng cho luồng chính. Chỉ thao tác khi UI và Backend cho phép theo trạng thái.

## 4. Quyền truy cập và cách trình diễn

| Vai trò | Kết quả cần kiểm tra |
|---|---|
| Chưa đăng nhập | Xem landing/services/booking; không mở khu vực nội bộ. Không gửi mutation để kiểm tra quyền trên DB thật. |
| Customer | Không vào workspace; không xem chi tiết phiếu/báo giá/hóa đơn của khách khác; không đọc danh mục khách hàng nội bộ. |
| Staff | Xác nhận/tiếp nhận/phân công, quản lý khách, lập hóa đơn/thu tiền/bàn giao; không quản lý dịch vụ/báo cáo nếu không có role manager/admin. |
| Technician | Phiếu sửa/chi tiết/tiếp nhận giới hạn theo phân công. **Được xem toàn bộ danh sách khách hàng theo xác nhận của người dùng trong lượt này**; không siết quyền catalog. Menu không hiển thị quản lý khách nhưng API hiện cho xem bằng quyền RequireStaff. |
| Manager | Quản lý dịch vụ/nhân sự/ca làm/báo cáo; `/admin` quản lý tài khoản vẫn yêu cầu is_superuser theo thiết kế hiện có. |
| Superuser | Vượt kiểm tra role theo Backend; không dùng để chứng minh role customer/staff/technician bị chặn đúng. |

Các quyền tạo/sửa khách hàng và duyệt báo giá của nhân sự được giữ theo chính sách Backend hiện có; lượt này không định nghĩa lại toàn bộ ma trận quyền. API hiện cho nhân sự được phép duyệt báo giá, vì vậy “khách duyệt” là thứ tự demo, chưa phải ràng buộc độc quyền customer của Backend.

Kiểm thử quyền gây thay đổi dữ liệu chạy trong SQLite tách biệt. Chưa có tài khoản demo riêng nên không báo đã xác minh đủ bốn vai trò trên PostgreSQL runtime.

### 4.1. Đối chiếu yêu cầu duyệt báo giá

Nguồn: `docs/project/QLDACNTT.docx`:

- **Mục 10.3 — Yêu cầu chức năng:** mô tả nhân viên lập báo giá, kỹ thuật viên cập nhật chẩn đoán/kết quả và quản lý quản trị báo giá. Không ghi quyền duyệt là độc quyền khách hàng.
- **Mục 10.5 — Quy tắc nghiệp vụ:** yêu cầu chuyển trạng thái hợp lệ, cập nhật đúng phạm vi được phân công và lưu thời gian/người thực hiện khi duyệt báo giá hoặc hoàn tất. Không quy định rõ điều kiện `ACCEPTED` trước `COMPLETED`.
- **Mục 13.3 — Luồng trải nghiệm chính:** mô tả thứ tự nội bộ tiếp nhận → phân công → chẩn đoán → báo giá → sửa chữa → thanh toán → bàn giao. Luồng khách có xem báo giá; chưa nêu bước bắt buộc khách duyệt.
- **Mục 13.4 — Màn hình quản lý báo giá:** mục đích là tạo, xem, duyệt; không chỉ định người duyệt cuối cùng hoặc ngoại lệ duyệt hộ.

**Kết luận:** chưa đủ căn cứ để tự thêm ràng buộc bắt buộc khách duyệt trước hoàn tất. Giữ nguyên Backend và Frontend của nghiệp vụ báo giá. UI hiện hiển thị trạng thái SENT/ACCEPTED/REJECTED tương ứng “Đã gửi”/“Đã duyệt”/“Từ chối”, làm mới sau thao tác thành công. Không thêm chặn giả chỉ ở Frontend.

Demo chủ động để customer duyệt ở bước 8 rồi technician mới hoàn tất ở bước 9. Cần trình bày đúng: đây là thứ tự thao tác demo, **chưa phải ràng buộc được Backend cưỡng chế**. Nếu nhóm xác nhận yêu cầu bắt buộc, cần chốt thêm: ai được duyệt, có cho nhân viên duyệt hộ không, và dùng báo giá nào nếu một phiếu có nhiều báo giá. Sau đó mới bổ sung kiểm tra Backend và UI cùng test; không tự đổi trong lượt này.

## 5. Lỗi thực tế đã sửa trong lượt readiness

- **Intake thiếu assigned scope:** test kỹ thuật viên chưa phân công nhận HTTP 201 thay vì 403. Thêm `check_appointment_access` trước mọi cập nhật trong tiếp nhận lịch có sẵn. Khách/unassigned tech bị chặn, assigned tech vẫn được tiếp nhận theo chính sách hiện có.
- **Phân công kỹ thuật viên không có phone trả 500:** model cho phone tùy chọn nhưng response yêu cầu string. Trả chuỗi rỗng khi chưa có phone, không bịa số, không đổi schema/endpoint. API chain đã bao phủ ca không nhập phone.

Không đổi routing/authentication architecture, không sửa generated client/dependency/database.

## 6. Kiểm thử lượt này

- Backend: 58/58 PASS (SQLite; demo/intake/repair/commerce/role tests), exit 0.
- Playwright: 22/22 PASS, exit 0; public readiness gọi GET API thật, 21 case còn lại dùng API mock, không tạo lịch/thu tiền thật.
- TypeScript và production build PASS; Biome read-only trên spec mới PASS; Ruff lint/format trên file Python thay đổi PASS; diff check PASS.
- E2E ghi nghiệp vụ PostgreSQL: BLOCKED do chưa có dữ liệu demo và chưa được phép tạo. Không đổi thành DONE cho các UID E2E.

## 7. ZIP bàn giao sạch

Tạo từ thư mục gốc, không cần thêm dependency:

```powershell
.venv/Scripts/python.exe scripts/package_handoff.py
```

Script chọn file Git đã theo dõi cộng danh sách tường minh các file readiness mới; không nén đệ quy cả workspace. Lấy **nội dung working tree hiện tại**, gồm thay đổi chưa commit nếu có. ZIP có thư mục `FixCare/` và `HANDOFF-MANIFEST.json` liệt kê file/SHA-256 và commit nền. Hai hotfix nay đã ở commit `1386e20`; ZIP tạo trong lượt readiness trước là snapshot cũ, chưa chứa cập nhật tài liệu final preparation này. Không tự ghi đè ZIP cũ; chạy lại script khi cần bản bàn giao mới.

Loại `.env` ở mọi cấp (kể cả example), `.git`, cấu hình AI/IDE local, dependencies/venv, `.tanstack`, auth state, test report/cache, log/file tạm, key/cert, dump/database và build output. Kiểm tra CRC, từng SHA-256, danh sách entry và một số mẫu token/private key trước khi báo thành công. Đây không phải chứng nhận scanner bảo mật toàn diện.

ZIP ở `artifacts/`, có SHA-256 in ra để đối chiếu. Không đưa ZIP hoặc artifacts vào Git. Lượt final preparation chỉ commit bốn file hotfix/test đã nêu; không push/deploy.

Người nhận phải cài dependencies bằng `bun install --frozen-lockfile` và `uv sync`, rồi tự cấu hình môi trường riêng. ZIP **không kèm database, tài khoản, mật khẩu hoặc dữ liệu demo**. Các tên cấu hình bắt buộc của Backend: PROJECT_NAME, SECRET_KEY, DATABASE_URL, FIRST_SUPERUSER, FIRST_SUPERUSER_PASSWORD; Docker còn cần POSTGRES_PASSWORD và các biến mail/domain theo compose. Frontend cần cấu hình riêng `VITE_API_URL=http://127.0.0.1:8000` khi chạy Vite trên host. Không có biến này thì URL tương đối không tự đi qua proxy của Vite hiện tại.

Không chép .env local vào bản bàn giao. Nếu máy nhận chưa có database/schema, phối hợp người phụ trách Backend để khởi tạo môi trường mới có phê duyệt; không chạy seed/migration tự động từ ZIP.

## 8. Hạn chế còn lại

- Chưa đủ dữ liệu PostgreSQL để demo thật; cần người dùng thực hiện mục 2, rồi xác minh lại với script và UI.
- Chẩn đoán dùng chung IN_PROGRESS; Backend chưa bắt buộc chỉ được sửa/hoàn tất sau khi customer duyệt. Demo tuân thủ đúng thứ tự ở bảng, không nói rằng hệ thống đã cưỡng chế quy tắc chưa có.
- Chưa test concurrency PostgreSQL, SMTP round-trip, in/PDF thực, Firefox/WebKit hoặc deployment. Nút in hiện in danh sách hóa đơn, không phải hóa đơn thuế.
- Một số dropdown giới hạn 100 bản ghi. Cache .tanstack từ commit cũ còn ngoài phạm vi; bị loại khỏi ZIP.
- Quyền xem catalog khách của technician được giữ nguyên theo xác nhận, khác với quyền thao tác phiếu được giao.

Đọc tài liệu này trước khi demo; [demo cũ](hung-fast-track-demo.md) vẫn giữ giải thích kiến trúc và lệnh khởi động.

## 9. Checklist demo cuối cùng

Các ô đã đánh dấu là kiểm tra kỹ thuật đã thực hiện. Ô chưa đánh dấu cần **bạn thao tác thủ công** trên môi trường local/test được phép; agent chưa tạo dữ liệu hay thử thu tiền thật.

### A. Đã chốt kỹ thuật

- [x] Review diff hai hotfix; commit cục bộ đúng 4 file: `1386e20`.
- [x] Backend 35/35 PASS trên SQLite tách biệt; Ruff PASS.
- [x] Playwright duyệt báo giá/thông báo 1/1 PASS bằng mock API.
- [x] Đối chiếu DOCX, giữ nguyên quy tắc báo giá vì chưa có yêu cầu chặn rõ ràng.
- [x] Đọc số lượng dữ liệu PostgreSQL trong transaction READ ONLY; không seed/reset/sửa .env.

### B. Bạn chuẩn bị dữ liệu

- [ ] Mở Frontend tại `http://localhost:5173`; Backend chạy ở `http://127.0.0.1:8000`.
- [ ] Superuser → `/admin` → **Add User**: nhập họ tên, email, mật khẩu và xác nhận; chọn role `customer`, bật **Is active?**, tắt **Is superuser?** → **Save**. Không ghi mật khẩu vào checklist.
- [ ] Lặp lại **Add User** cho `staff`, `technician`, `manager`; email của từng tài khoản khác nhau. Không sửa tài khoản superuser đang dùng.
- [ ] Manager → `/workspace/services`: tên dịch vụ (ví dụ Thay pin demo), giá **100000**, thời lượng **30**, **Đang cung cấp** → **Lưu dịch vụ**. Mở `/services` để thấy dịch vụ.
- [ ] Manager → `/workspace/technicians`: nhập tên, chọn đúng tài khoản technician active chưa liên kết → **Tạo kỹ thuật viên**. Số điện thoại tùy chọn, không cần bịa số.
- [ ] Chọn hồ sơ vừa tạo → chọn ngày demo tương lai (ví dụ **28/10/2026**), **08:00–17:00** → **Thêm ca làm việc**. Kiểm tra ca **AVAILABLE** đúng ngày.
- [ ] Tách bốn profile trình duyệt, đăng nhập đúng bốn tài khoản; manager không cần quyền superuser. Chỉ superuser dùng `/admin`.
- [ ] Chạy lại `.venv/Scripts/python.exe -W ignore scripts/check_demo_readiness.py` từ thư mục gốc; mong đợi `data_prerequisites_ready=true`, rồi kiểm tra slot thực tế trên UI. Cờ này không thay thế kiểm thử demo.

### C. Bạn thực hiện luồng chính

- [ ] **Customer `/booking`**: chọn dịch vụ/ngày/slot API đang trả, nhập liên hệ và thiết bị → **Xác nhận đặt lịch**. Ghi mã APPT hiển thị.
- [ ] **Customer `/appointments`**: mở chi tiết đúng mã, kiểm tra lịch gắn với tài khoản; không tạo thêm phiếu vãng lai cho cùng máy.
- [ ] **Staff `/workspace/appointments`**: tìm mã APPT → **Xác nhận lịch** → xác nhận dialog, kiểm tra CONFIRMED.
- [ ] **Staff cùng lịch**: điền ngoại quan, lỗi, phụ kiện → **Tiếp nhận thiết bị**.
- [ ] **Staff `/workspace/repairs`**: chọn đúng APPT → chọn kỹ thuật viên liên kết → **Phân công kỹ thuật viên**.
- [ ] **Technician `/workspace/repairs`**: mở việc được giao → nhập chẩn đoán/ghi chú, chuyển IN_PROGRESS → **Cập nhật tiến độ** → xác nhận. Chưa thay linh kiện trước khi customer duyệt trong kịch bản demo.
- [ ] **Technician/Staff cùng phiếu**: nhập hạng mục/đơn giá/số lượng → **Tạo báo giá gửi khách**; ghi mã QUO và tổng tiền.
- [ ] **Customer `/quotes`**: kiểm tra đúng QUO → **Duyệt báo giá** → xác nhận, kiểm tra **Đã duyệt**.
- [ ] **Technician cùng phiếu**: sau sửa/kiểm tra máy, chọn COMPLETED, ghi kết quả → **Cập nhật tiến độ** → xác nhận. Không gửi IN_PROGRESS lần nữa nếu đang ở trạng thái đó.
- [ ] **Staff `/invoices`**: chọn đúng báo giá ACCEPTED của phiếu COMPLETED → **Lập hóa đơn**.
- [ ] **Staff cùng hóa đơn**: nhập đúng số tiền đã nhận, CASH hoặc BANK_TRANSFER → **Ghi nhận thanh toán** → xác nhận. Đây là ghi nhận tại quầy, không phải cổng chuyển tiền. Kiểm tra PAID và số dư 0.
- [ ] **Staff**: khi PAID → **Bàn giao thiết bị** → xác nhận; kiểm tra thông báo thành công.
- [ ] **Customer `/invoices`, `/notifications`**: xem hóa đơn/khoản thu của mình và thông báo bàn giao.
- [ ] **Manager `/workspace/reports`**: chọn khoảng ngày có thanh toán, kiểm tra doanh thu thực thu; có thể xuất CSV.

### D. Trước khi trình bày

- [ ] Không hiển thị .env, password, token, tab DevTools chứa header Authorization hoặc auth state trước người xem.
- [ ] Không dùng superuser để chứng minh phân quyền; giữ quyền technician xem toàn bộ danh mục khách theo xác nhận trước đó.
- [ ] Không nói đã có cổng thanh toán online, hóa đơn thuế/PDF riêng hoặc chặn hoàn tất trước duyệt nếu hệ thống chưa có.
- [ ] Nếu gặp lỗi, ghi bước/route/mã trạng thái đã loại thông tin nhạy cảm; không reset/seed hoặc tự sửa database để che lỗi.
- [ ] Chỉ đánh dấu hoàn thành demo PostgreSQL sau khi bạn thật sự đi hết luồng C. Hiện luồng này vẫn **chưa chạy** do thiếu dữ liệu và quyền tạo dữ liệu chưa cấp cho agent.
