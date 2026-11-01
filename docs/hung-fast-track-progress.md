# FixCare — Fast-track progress

> Demo readiness 27/10/2026: môi trường PASS; dữ liệu PostgreSQL chưa sẵn sàng (dịch vụ active, 4 role riêng, linked technician và ca AVAILABLE đều 0). Không tự tạo dữ liệu. Hai lỗi thực tế intake thiếu scope và phân công thiếu phone đã sửa; Backend 58/58, Playwright 22/22 PASS. Giữ chính sách technician xem toàn bộ catalog khách theo xác nhận người dùng. Hướng dẫn nhập qua UI, bước demo và đóng ZIP sạch tại [readiness](hung-demo-readiness.md). Không tự commit/push trong lượt này; thay đổi mới nằm trong working tree và bản ZIP.

Cập nhật 27/10/2026. Bảng đầy đủ giữ nguyên 108 UID/WBS/Sprint/tên/thứ tự Excel: [status](hung-fast-track-status.md). Bằng chứng: [verification](hung-fast-track-verification.md). Khởi động, demo và bàn giao: [demo](hung-fast-track-demo.md).

## Kết quả hiện tại

- **72 DONE / 28 PARTIAL / 8 BLOCKED / 0 TODO** theo bảng 108 task. DONE là nghiệm thu kỹ thuật phần được test; không đồng nghĩa đã nghiệm thu nhóm/deploy hay E2E ghi PostgreSQL.
- UID 767 (`c5b53b8`), 772 (`55d9030`), 770 (`486394b`) được giữ nguyên. UID 770 đã xác minh hoàn thành; không làm lại HTTP client.
- Nhóm A: token refresh/rotation, đăng nhập/đăng ký/hồ sơ được tái dùng. Sửa thêm việc cache dữ liệu riêng còn tồn tại sau logout, có test tái hiện FAIL trước sửa và PASS sau sửa.
- Nhóm B: tạo lịch, chọn kỹ thuật viên tùy chọn, danh sách/chi tiết lịch của mình, đổi/hủy hợp lệ. Đã sửa route cha thiếu Outlet bằng index route, kiểm tra cả click link và reload URL chi tiết.
- Nhóm C: dashboard/KPI, tìm/lọc/danh sách/chi tiết/confirm/reschedule/cancel/assign, hàng chờ và đặt chỗ nhanh, hồ sơ khách, kỹ thuật viên và ca làm việc.
- Nhóm D: tiếp nhận từ lịch hoặc vãng lai, thiết bị, chẩn đoán/ghi chú, báo giá nhiều hạng mục/duyệt/từ chối, phiếu sửa và việc kỹ thuật viên theo phân công.
- Nhóm E: hóa đơn từ quote ACCEPTED sau COMPLETED, thu tiền tại quầy, lịch sử khoản thu/bàn giao, review/notification riêng, quản trị tài khoản/role, dịch vụ, báo cáo/doanh thu/CSV.
- Công khai: landing/layout giữ nguyên; bổ sung `/services`, `/services/<id>` và `/about`, dữ liệu dịch vụ từ API.
- Không có cổng thanh toán online; không giả lập đã chuyển tiền. Không thêm dependency, migration, seed hoặc thay đổi .env.

## API và dữ liệu thật

OpenAPI runtime: **HTTP 200 / 70 path / 93 operation / 0 operationId trùng**; schema snapshot `frontend/openapi.json` và generated client đồng bộ.

- Public services/list/detail; slots available/check và technician choices chỉ có id/tên/chuyên môn.
- Appointments create/me/detail/history/update/confirm/cancel/assign; queue và intake.
- Customers, technicians CRUD/status, work-schedules; `GET /technicians/accounts` chỉ quản lý, chọn tài khoản active chưa liên kết.
- Devices update; repair-orders list/detail/status/assign; quotes list/detail/create/accept/reject.
- Invoices list/detail/issue, payments với request_id chống lặp/khóa hóa đơn/chặn thu dư, handover chỉ sau PAID.
- Reviews owner sau COMPLETED và chống trùng; notifications lọc user/customer; statistics RequireManager dựa trên payments SUCCESS.
- Không dùng customer_id tùy ý để đọc lịch cá nhân. Backend checks owner/assigned technician cả detail/lookup/update/quote/repair/queue.
- Alias `/api/...` cũ vẫn có; OpenAPI chỉ công bố một bộ để generator ổn định.
- **PostgreSQL đang trả 0 dịch vụ active**. API catalog HTTP 200, không lỗi kết nối nhưng chưa đủ dữ liệu đặt lịch thật. Người phụ trách cần nhập dịch vụ/ca làm bằng UI trên môi trường cho phép; agent không tự tạo.

## Kiểm thử đã chạy

| Kiểm tra | Kết quả | Phạm vi |
|---|---|---|
| Backend regression | PASS 152/152, exit 0, 38,30s | Auth/users + slots/appointments/history + customers/technicians/schedules/queue/intake/quotes/repairs + commerce workflow; SQLite trong bộ nhớ. |
| Playwright tổng thể | PASS 48/48, exit 0, 2,2 phút | Auth setup, login, HTTP errors/refresh, landing/layout, booking, appointments, operations, services, account UI. |
| Hai dashboard bổ sung | PASS 2/2, exit 0, 5,5s | KPI nhân viên và việc kỹ thuật viên. |
| Sau hotfix cache phiên | PASS 22/22, exit 0, 57,9s | Auth setup + login + HTTP/refresh + 4 account cases (có đổi tài khoản). Trùng một phần với lượt 48, không cộng thành 72 test độc lập. |
| Tổng test trình duyệt khác nhau | PASS 51 case | Tính theo danh sách test hiện tại, qua các lượt trên; không phải một lệnh chạy 51 case. |
| TypeScript | PASS | `bunx tsc --noEmit -p tsconfig.build.json`; package không có script typecheck riêng. |
| Production build | PASS | `bun run build` (bao gồm tsc + Vite). |
| Biome read-only | PASS | Các file source/test/config thay đổi; không dùng script lint --write --unsafe toàn repo. |
| Ruff lint + format check | PASS | 27 file Python thay đổi so với trước fast-track. |
| Runtime contract/catalog | PASS | OpenAPI 200, operationId duy nhất; services 200, catalog rỗng. |
| Browser nghiệp vụ ghi PostgreSQL | NOT RUN | Không ghi lịch/đổi/hủy/thu tiền thật chỉ để test; cần database test riêng. |
| GitHub Actions/deploy/email Mailpit round-trip | NOT RUN | Không push/deploy; chưa kiểm tra mail thực tế. |

Bản build cuối sau hotfix cache được chạy lại trước commit; kết quả/lệnh và hạn chế xem verification. Kiểm thử không thay thế nghiệm thu nghiệp vụ của nhóm.

## Commit cục bộ

| Nhóm | Commit | Nội dung |
|---|---|---|
| B | `db24bc8` | Customer booking/appointment management và generator postProcess chuẩn hóa trailing whitespace. |
| C | `5f33005` | Reception workspace, lịch/hàng chờ/khách/nhân sự/ca làm. |
| D | `3c8fabc` | Repair/quote workflow và quyền owner/assigned. |
| E | `b091d37` | Invoice/payment/review/notifications/reporting và service/account management. |
| QA cuối/hardening | `eb50e81` | Scope queue/slot, technician choices/accounts, UX/semantic headings, cache logout và regression coverage. |

Không push. Không stage cache .tanstack, auth state, .env hoặc báo cáo chứa token. Cache .tanstack đã tracked từ commit cũ vẫn có thể làm working tree không sạch; không đưa vào commit mới.

## Phần còn lại, không tự nhận hoàn thành

- 7 UID tích hợp Sprint: chưa có E2E browser ghi PostgreSQL test riêng; API chain đã PASS SQLite.
- Acceptance/DoD Sprint và một số UID UI hoàn chỉnh còn PARTIAL vì chưa phủ mọi viewport/nhánh lỗi/wireframe và xác nhận nhóm.
- UID 780: cần email Mailpit round-trip thực tế; UID 902: workflow cần chạy GitHub thật; UID 831: cần xác nhận nhận bàn giao.
- UID 2016/2031/2046/2061/2077/2093/2109: cần họp thật/biên bản. UID 830: cần xác nhận release từ người phụ trách.
- In hiện là danh sách hóa đơn qua trình duyệt, chưa có PDF hóa đơn riêng/thuế; concurrency PostgreSQL chưa test; dropdown có giới hạn 100 ở một số màn.
- Dữ liệu local có thể `role=customer` nhưng `is_superuser=true`: không tự sửa DB; quyền superuser là bypass Backend hiện có. Dùng tài khoản role riêng khi demo.

## Hướng dẫn tiếp tục

Ưu tiên cấp database PostgreSQL test độc lập và dữ liệu demo được người dùng nhập qua UI; sau đó test xuyên vai trò khách → nhân viên → kỹ thuật viên → thu tiền. Không triển khai lại các route đã làm. Lệnh/prompt tiếp tục trong [demo](hung-fast-track-demo.md).
