# FixCare — Trạng thái hiện tại của đủ 108 task Hưng

Cập nhật 27/10/2026. Nguồn UID/WBS/Sprint/tên/thứ tự: `docs/project/Task_cua_Hung.xlsx`. Giữ nguyên 108 dòng gốc, kể cả tên task trùng nhau. Đây là bảng hiện trạng bổ sung; audit 26/10 là mốc lịch sử, không phải trạng thái hiện tại.

- DONE: phạm vi kỹ thuật tương ứng đã có mã và bằng chứng chạy phù hợp (có thể gồm UI mock + API test cô lập); không đồng nghĩa đã E2E ghi PostgreSQL hay được nhóm nghiệm thu.
- PARTIAL: đã có mã/bằng chứng một phần, còn tiêu chí ghi rõ ở từng dòng.
- BLOCKED: cần bằng chứng/điều kiện bên ngoài chưa được phép tự tạo.
- TODO: chưa triển khai. Không dùng DONE chỉ vì có file.

Kết quả chi tiết và lệnh chạy: [verification](hung-fast-track-verification.md); thao tác demo: [demo](hung-fast-track-demo.md).

| Sprint | DONE | PARTIAL | BLOCKED | TODO |
|---|---:|---:|---:|---:|
| Sprint 1 | 16 | 4 | 1 | 0 |
| Sprint 2 | 7 | 3 | 1 | 0 |
| Sprint 3 | 11 | 3 | 1 | 0 |
| Sprint 4 | 11 | 4 | 1 | 0 |
| Sprint 5 | 12 | 4 | 1 | 0 |
| Sprint 6 | 6 | 5 | 1 | 0 |
| Sprint 7 | 9 | 5 | 2 | 0 |

Tổng: 72 DONE / 28 PARTIAL / 8 BLOCKED / 0 TODO.

## Sprint 1

| # | UID | WBS | Sprint | Tên task (nguyên gốc) | Trạng thái | Bằng chứng / phần còn thiếu | File liên quan |
|---:|---:|---|---|---|---|---|---|
| 1 | 762 | 2.2.4 | Sprint 1 | Phân tích yêu cầu giao diện | DONE | Phân tích nghiệp vụ, luồng demo và thiết kế thống nhất đã lưu trong kế hoạch. | docs/hung-implementation-plan.md |
| 2 | 763 | 2.2.9 | Sprint 1 | Khởi tạo project frontend | DONE | Build/typecheck; kiểm thử route, responsive 375/768/1440, validation form trong bộ test cuối. | frontend/src/components/Operations/shared.tsx; frontend/src/routes/ |
| 3 | 764 | 2.2.13 | Sprint 1 | Thiết lập cấu trúc thư mục frontend | DONE | Build/typecheck; kiểm thử route, responsive 375/768/1440, validation form trong bộ test cuối. | frontend/src/components/Operations/shared.tsx; frontend/src/routes/ |
| 4 | 766 | 2.2.17 | Sprint 1 | Thiết lập component base | DONE | Build/typecheck; kiểm thử route, responsive 375/768/1440, validation form trong bộ test cuối. | frontend/src/components/Operations/shared.tsx; frontend/src/routes/ |
| 5 | 767 | 2.2.20 | Sprint 1 | Thiết lập layout chung | DONE | Nghiệm thu UID 767 + hồi quy layout/navigation/login. | docs/uid-767-acceptance.md; frontend/tests/layout-routing.spec.ts |
| 6 | 769 | 2.2.25 | Sprint 1 | Thiết lập form validation | DONE | Build/typecheck; kiểm thử route, responsive 375/768/1440, validation form trong bộ test cuối. | frontend/src/components/Operations/shared.tsx; frontend/src/routes/ |
| 7 | 770 | 2.2.30 | Sprint 1 | Thiết lập HTTP client | DONE | Generated client, Bearer/refresh, HTTP error tests; UID 770 ở 486394b, token ở 70a5b69. | frontend/src/main.tsx; frontend/src/utils.ts; frontend/tests/http-error-handling.spec.ts |
| 8 | 776 | 2.2.37 | Sprint 1 | Tạo trang danh sách dịch vụ | DONE | services.spec: danh sách → chi tiết → reload → link booking; mở giới thiệu. | frontend/src/routes/services.tsx; frontend/src/routes/services_.$serviceId.tsx; frontend/src/routes/about.tsx |
| 9 | 765 | 2.2.43 | Sprint 1 | Thiết lập routing | DONE | Build/typecheck; kiểm thử route, responsive 375/768/1440, validation form trong bộ test cuối. | frontend/src/components/Operations/shared.tsx; frontend/src/routes/ |
| 10 | 768 | 2.2.49 | Sprint 1 | Thiết lập responsive grid | DONE | Build/typecheck; kiểm thử route, responsive 375/768/1440, validation form trong bộ test cuối. | frontend/src/components/Operations/shared.tsx; frontend/src/routes/ |
| 11 | 772 | 2.2.54 | Sprint 1 | Tạo trang Landing | DONE | Nghiệm thu UID 772, commit 55d9030; hồi quy landing. | docs/uid-772-acceptance.md; frontend/tests/landing.spec.ts |
| 12 | 773 | 2.2.57 | Sprint 1 | Tạo Header | DONE | Nghiệm thu UID 767 + hồi quy layout/navigation/login. | docs/uid-767-acceptance.md; frontend/tests/layout-routing.spec.ts |
| 13 | 774 | 2.2.60 | Sprint 1 | Tạo Footer | DONE | Nghiệm thu UID 767 + hồi quy layout/navigation/login. | docs/uid-767-acceptance.md; frontend/tests/layout-routing.spec.ts |
| 14 | 775 | 2.2.63 | Sprint 1 | Tạo trang giới thiệu cửa hàng | DONE | services.spec: danh sách → chi tiết → reload → link booking; mở giới thiệu. | frontend/src/routes/services.tsx; frontend/src/routes/services_.$serviceId.tsx; frontend/src/routes/about.tsx |
| 15 | 777 | 2.2.67 | Sprint 1 | Tạo trang chi tiết dịch vụ | DONE | services.spec: danh sách → chi tiết → reload → link booking; mở giới thiệu. | frontend/src/routes/services.tsx; frontend/src/routes/services_.$serviceId.tsx; frontend/src/routes/about.tsx |
| 16 | 902 | 2.2.69 | Sprint 1 | Thiết lập CI/CD React và build frontend tự động | PARTIAL | Đã có workflow build/smoke và artifact; chưa chạy GitHub Actions hoặc deploy, không push. | .github/workflows/frontend-quality.yml |
| 17 | 2024 | 2.3.1 | Sprint 1 | Tích hợp đầu-cuối Sprint 1: React ↔ FastAPI ↔ PostgreSQL | PARTIAL | API workflow đã chạy trên SQLite + UI mock; PostgreSQL chỉ đọc schema/catalog và login thật. Chưa chạy browser ghi nghiệp vụ end-to-end vào PostgreSQL test. | backend/tests/api/routes/test_commerce_workflow.py; frontend/tests/; docs/hung-fast-track-progress.md |
| 18 | 2025 | 2.3.2 | Sprint 1 | Kiểm thử acceptance và hồi quy Sprint 1 | PARTIAL | Đã hồi quy các luồng chính; chưa phủ mọi acceptance criterion/biên dữ liệu/role/viewport trong Excel. | docs/hung-fast-track-verification.md |
| 19 | 2027 | 2.3.4 | Sprint 1 | Sửa lỗi frontend theo kết quả kiểm thử Sprint 1 | DONE | Các lỗi phát hiện trong lượt QA đã phân loại/sửa/retest; xem bug log, không có lỗi đỏ còn mở trong bộ test đã chạy. | docs/hung-fast-track-verification.md |
| 20 | 2029 | 2.3.6 | Sprint 1 | Retest, xác minh Definition of Done Sprint 1 | PARTIAL | Đã có retest kỹ thuật; chưa xác nhận toàn bộ Definition of Done của Sprint do E2E PostgreSQL và nghiệm thu nhóm còn thiếu. | docs/hung-fast-track-verification.md |
| 21 | 2016 | 2.4.1 | Sprint 1 | Họp tuần 1 – báo cáo tiến độ, demo và thống nhất việc tiếp theo | BLOCKED | Cần cuộc họp/demo thật và biên bản của thành viên; không thể tự tạo bằng chứng họp. | — |

## Sprint 2

| # | UID | WBS | Sprint | Tên task (nguyên gốc) | Trạng thái | Bằng chứng / phần còn thiếu | File liên quan |
|---:|---:|---|---|---|---|---|---|
| 22 | 771 | 3.2.3 | Sprint 2 | Thiết lập xử lý token | DONE | Generated client, Bearer/refresh, HTTP error tests; UID 770 ở 486394b, token ở 70a5b69. | frontend/src/main.tsx; frontend/src/utils.ts; frontend/tests/http-error-handling.spec.ts |
| 23 | 778 | 3.2.14 | Sprint 2 | Tạo trang đăng ký | DONE | Đăng ký qua mock UI đúng payload/redirect; Backend users tests trong SQLite. | frontend/tests/account-flows.spec.ts; frontend/src/routes/signup.tsx; backend/tests/api/routes/test_users.py |
| 24 | 779 | 3.2.17 | Sprint 2 | Tạo trang đăng nhập | DONE | Auth setup và 10 login tests với Backend local; HTTP error regression. | frontend/tests/auth.setup.ts; frontend/tests/login.spec.ts |
| 25 | 781 | 3.2.19 | Sprint 2 | Tạo trang hồ sơ cá nhân | DONE | Sửa hồ sơ; API lỗi giữ input, thử lại thành công; Backend users tests. | frontend/tests/account-flows.spec.ts; frontend/src/components/UserSettings/UserInformation.tsx |
| 26 | 824 | 3.2.21 | Sprint 2 | Kết nối API đăng ký | DONE | Đăng ký qua mock UI đúng payload/redirect; Backend users tests trong SQLite. | frontend/tests/account-flows.spec.ts; frontend/src/routes/signup.tsx; backend/tests/api/routes/test_users.py |
| 27 | 825 | 3.2.23 | Sprint 2 | Kết nối API đăng nhập | DONE | Auth setup và 10 login tests với Backend local; HTTP error regression. | frontend/tests/auth.setup.ts; frontend/tests/login.spec.ts |
| 28 | 2039 | 3.3.1 | Sprint 2 | Tích hợp đầu-cuối Sprint 2: React ↔ FastAPI ↔ PostgreSQL | PARTIAL | API workflow đã chạy trên SQLite + UI mock; PostgreSQL chỉ đọc schema/catalog và login thật. Chưa chạy browser ghi nghiệp vụ end-to-end vào PostgreSQL test. | backend/tests/api/routes/test_commerce_workflow.py; frontend/tests/; docs/hung-fast-track-progress.md |
| 29 | 2040 | 3.3.2 | Sprint 2 | Kiểm thử acceptance và hồi quy Sprint 2 | PARTIAL | Đã hồi quy các luồng chính; chưa phủ mọi acceptance criterion/biên dữ liệu/role/viewport trong Excel. | docs/hung-fast-track-verification.md |
| 30 | 2042 | 3.3.4 | Sprint 2 | Sửa lỗi frontend theo kết quả kiểm thử Sprint 2 | DONE | Các lỗi phát hiện trong lượt QA đã phân loại/sửa/retest; xem bug log, không có lỗi đỏ còn mở trong bộ test đã chạy. | docs/hung-fast-track-verification.md |
| 31 | 2044 | 3.3.6 | Sprint 2 | Retest, xác minh Definition of Done Sprint 2 | PARTIAL | Đã có retest kỹ thuật; chưa xác nhận toàn bộ Definition of Done của Sprint do E2E PostgreSQL và nghiệm thu nhóm còn thiếu. | docs/hung-fast-track-verification.md |
| 32 | 2031 | 3.4.1 | Sprint 2 | Họp tuần 2 – báo cáo tiến độ, demo và thống nhất việc tiếp theo | BLOCKED | Cần cuộc họp/demo thật và biên bản của thành viên; không thể tự tạo bằng chứng họp. | — |

## Sprint 3

| # | UID | WBS | Sprint | Tên task (nguyên gốc) | Trạng thái | Bằng chứng / phần còn thiếu | File liên quan |
|---:|---:|---|---|---|---|---|---|
| 33 | 786 | 4.2.4 | Sprint 3 | Tạo giao diện kiểm tra slot trống | DONE | booking.spec 3 cases: dịch vụ/ngày/giờ, tùy chọn kỹ thuật viên, payload, success/error/double-submit; Backend slot tests. | frontend/src/routes/booking.tsx; frontend/tests/booking.spec.ts |
| 34 | 782 | 4.2.12 | Sprint 3 | Tạo trang chọn dịch vụ | DONE | booking.spec 3 cases: dịch vụ/ngày/giờ, tùy chọn kỹ thuật viên, payload, success/error/double-submit; Backend slot tests. | frontend/src/routes/booking.tsx; frontend/tests/booking.spec.ts |
| 35 | 783 | 4.2.17 | Sprint 3 | Tạo giao diện chọn ngày | DONE | booking.spec 3 cases: dịch vụ/ngày/giờ, tùy chọn kỹ thuật viên, payload, success/error/double-submit; Backend slot tests. | frontend/src/routes/booking.tsx; frontend/tests/booking.spec.ts |
| 36 | 784 | 4.2.21 | Sprint 3 | Tạo giao diện chọn giờ | DONE | booking.spec 3 cases: dịch vụ/ngày/giờ, tùy chọn kỹ thuật viên, payload, success/error/double-submit; Backend slot tests. | frontend/src/routes/booking.tsx; frontend/tests/booking.spec.ts |
| 37 | 785 | 4.2.24 | Sprint 3 | Tạo giao diện chọn kỹ thuật viên | DONE | booking.spec 3 cases: dịch vụ/ngày/giờ, tùy chọn kỹ thuật viên, payload, success/error/double-submit; Backend slot tests. | frontend/src/routes/booking.tsx; frontend/tests/booking.spec.ts |
| 38 | 788 | 4.2.25 | Sprint 3 | Tạo màn hình xác nhận lịch | DONE | booking.spec 3 cases: dịch vụ/ngày/giờ, tùy chọn kỹ thuật viên, payload, success/error/double-submit; Backend slot tests. | frontend/src/routes/booking.tsx; frontend/tests/booking.spec.ts |
| 39 | 787 | 4.2.26 | Sprint 3 | Tạo form đặt lịch | DONE | booking.spec 3 cases: dịch vụ/ngày/giờ, tùy chọn kỹ thuật viên, payload, success/error/double-submit; Backend slot tests. | frontend/src/routes/booking.tsx; frontend/tests/booking.spec.ts |
| 40 | 789 | 4.2.28 | Sprint 3 | Tạo màn hình lịch đã đặt | DONE | appointments.spec: link danh sách, direct/reload detail, hủy xác nhận và đổi giờ; Backend owner + history tests. | frontend/src/routes/_layout/appointments/; frontend/src/routes/_layout/appointments.$appointmentId.tsx; frontend/tests/appointments.spec.ts |
| 41 | 790 | 4.2.29 | Sprint 3 | Tạo chức năng đổi lịch | DONE | appointments.spec: link danh sách, direct/reload detail, hủy xác nhận và đổi giờ; Backend owner + history tests. | frontend/src/routes/_layout/appointments/; frontend/src/routes/_layout/appointments.$appointmentId.tsx; frontend/tests/appointments.spec.ts |
| 42 | 791 | 4.2.31 | Sprint 3 | Tạo chức năng hủy lịch | DONE | appointments.spec: link danh sách, direct/reload detail, hủy xác nhận và đổi giờ; Backend owner + history tests. | frontend/src/routes/_layout/appointments/; frontend/src/routes/_layout/appointments.$appointmentId.tsx; frontend/tests/appointments.spec.ts |
| 43 | 2054 | 4.3.1 | Sprint 3 | Tích hợp đầu-cuối Sprint 3: React ↔ FastAPI ↔ PostgreSQL | PARTIAL | API workflow đã chạy trên SQLite + UI mock; PostgreSQL chỉ đọc schema/catalog và login thật. Chưa chạy browser ghi nghiệp vụ end-to-end vào PostgreSQL test. | backend/tests/api/routes/test_commerce_workflow.py; frontend/tests/; docs/hung-fast-track-progress.md |
| 44 | 2055 | 4.3.2 | Sprint 3 | Kiểm thử acceptance và hồi quy Sprint 3 | PARTIAL | Đã hồi quy các luồng chính; chưa phủ mọi acceptance criterion/biên dữ liệu/role/viewport trong Excel. | docs/hung-fast-track-verification.md |
| 45 | 2057 | 4.3.4 | Sprint 3 | Sửa lỗi frontend theo kết quả kiểm thử Sprint 3 | DONE | Các lỗi phát hiện trong lượt QA đã phân loại/sửa/retest; xem bug log, không có lỗi đỏ còn mở trong bộ test đã chạy. | docs/hung-fast-track-verification.md |
| 46 | 2059 | 4.3.6 | Sprint 3 | Retest, xác minh Definition of Done Sprint 3 | PARTIAL | Đã có retest kỹ thuật; chưa xác nhận toàn bộ Definition of Done của Sprint do E2E PostgreSQL và nghiệm thu nhóm còn thiếu. | docs/hung-fast-track-verification.md |
| 47 | 2046 | 4.4.1 | Sprint 3 | Họp tuần 3 – báo cáo tiến độ, demo và thống nhất việc tiếp theo | BLOCKED | Cần cuộc họp/demo thật và biên bản của thành viên; không thể tự tạo bằng chứng họp. | — |

## Sprint 4

| # | UID | WBS | Sprint | Tên task (nguyên gốc) | Trạng thái | Bằng chứng / phần còn thiếu | File liên quan |
|---:|---:|---|---|---|---|---|---|
| 48 | 804 | 5.2.4 | Sprint 4 | Tạo màn hình danh sách lịch hẹn | DONE | Nhân viên đọc/confirm lịch; bộ API history/confirm/cancel/update và quyền; form đổi lịch theo contract. | frontend/src/routes/_layout/workspace/appointments.tsx; frontend/tests/operations.spec.ts |
| 49 | 793 | 5.2.10 | Sprint 4 | Tạo màn hình hàng chờ | DONE | Mock UI đặt chỗ nhanh → hàng chờ; Backend queue API tests; lọc ngày/phân trang. | frontend/src/routes/_layout/workspace/queue.tsx; backend/tests/api/routes/test_queue_api.py |
| 50 | 802 | 5.2.14 | Sprint 4 | Tạo dashboard nhân viên | DONE | UI xác minh KPI từ API và link xử lý; query đếm PENDING/CONFIRMED/queue/customers. | frontend/src/routes/_layout/workspace/index.tsx; frontend/tests/operations.spec.ts |
| 51 | 803 | 5.2.18 | Sprint 4 | Tạo màn hình quản lý lịch | DONE | Nhân viên đọc/confirm lịch; bộ API history/confirm/cancel/update và quyền; form đổi lịch theo contract. | frontend/src/routes/_layout/workspace/appointments.tsx; frontend/tests/operations.spec.ts |
| 52 | 805 | 5.2.22 | Sprint 4 | Tạo màn hình chi tiết lịch hẹn | DONE | Nhân viên đọc/confirm lịch; bộ API history/confirm/cancel/update và quyền; form đổi lịch theo contract. | frontend/src/routes/_layout/workspace/appointments.tsx; frontend/tests/operations.spec.ts |
| 53 | 812 | 5.2.24 | Sprint 4 | Tạo màn hình lịch làm việc kỹ thuật viên | DONE | UI chọn tài khoản/đổi giờ ca; Backend technicians/work schedules CRUD/quyền; không nhập ID tùy tiện. | frontend/src/routes/_layout/workspace/technicians.tsx; backend/tests/api/routes/test_technicians_api.py; backend/tests/api/routes/test_work_schedules_api.py |
| 54 | 792 | 5.2.28 | Sprint 4 | Tạo màn hình đặt chỗ | DONE | Mock UI đặt chỗ nhanh → hàng chờ; Backend queue API tests; lọc ngày/phân trang. | frontend/src/routes/_layout/workspace/queue.tsx; backend/tests/api/routes/test_queue_api.py |
| 55 | 2008 | 5.2.29 | Sprint 4 | Thiết kế UI hoàn chỉnh hàng chờ và quản lý lịch từ wireframe | PARTIAL | UI dùng component/token thật, form và hàng chờ đã test; chưa có xác nhận đối chiếu wireframe từ nhóm. | frontend/src/routes/_layout/workspace/; docs/hung-implementation-plan.md |
| 56 | 816 | 5.2.30 | Sprint 4 | Tạo màn hình quản lý kỹ thuật viên | DONE | UI chọn tài khoản/đổi giờ ca; Backend technicians/work schedules CRUD/quyền; không nhập ID tùy tiện. | frontend/src/routes/_layout/workspace/technicians.tsx; backend/tests/api/routes/test_technicians_api.py; backend/tests/api/routes/test_work_schedules_api.py |
| 57 | 817 | 5.2.32 | Sprint 4 | Tạo màn hình quản lý khách hàng | DONE | UI validation, tạo khách và refresh danh sách; Backend customer search/update/roles. | frontend/src/routes/_layout/workspace/customers.tsx; frontend/tests/operations.spec.ts |
| 58 | 819 | 5.2.33 | Sprint 4 | Tạo màn hình quản lý lịch | DONE | UI chọn tài khoản/đổi giờ ca; Backend technicians/work schedules CRUD/quyền; không nhập ID tùy tiện. | frontend/src/routes/_layout/workspace/technicians.tsx; backend/tests/api/routes/test_technicians_api.py; backend/tests/api/routes/test_work_schedules_api.py |
| 59 | 2069 | 5.3.1 | Sprint 4 | Tích hợp đầu-cuối Sprint 4: React ↔ FastAPI ↔ PostgreSQL | PARTIAL | API workflow đã chạy trên SQLite + UI mock; PostgreSQL chỉ đọc schema/catalog và login thật. Chưa chạy browser ghi nghiệp vụ end-to-end vào PostgreSQL test. | backend/tests/api/routes/test_commerce_workflow.py; frontend/tests/; docs/hung-fast-track-progress.md |
| 60 | 2070 | 5.3.2 | Sprint 4 | Kiểm thử acceptance và hồi quy Sprint 4 | PARTIAL | Đã hồi quy các luồng chính; chưa phủ mọi acceptance criterion/biên dữ liệu/role/viewport trong Excel. | docs/hung-fast-track-verification.md |
| 61 | 2072 | 5.3.4 | Sprint 4 | Sửa lỗi frontend theo kết quả kiểm thử Sprint 4 | DONE | Các lỗi phát hiện trong lượt QA đã phân loại/sửa/retest; xem bug log, không có lỗi đỏ còn mở trong bộ test đã chạy. | docs/hung-fast-track-verification.md |
| 62 | 2074 | 5.3.6 | Sprint 4 | Retest, xác minh Definition of Done Sprint 4 | PARTIAL | Đã có retest kỹ thuật; chưa xác nhận toàn bộ Definition of Done của Sprint do E2E PostgreSQL và nghiệm thu nhóm còn thiếu. | docs/hung-fast-track-verification.md |
| 63 | 2061 | 5.4.1 | Sprint 4 | Họp tuần 4 – báo cáo tiến độ, demo và thống nhất việc tiếp theo | BLOCKED | Cần cuộc họp/demo thật và biên bản của thành viên; không thể tự tạo bằng chứng họp. | — |

## Sprint 5

| # | UID | WBS | Sprint | Tên task (nguyên gốc) | Trạng thái | Bằng chứng / phần còn thiếu | File liên quan |
|---:|---:|---|---|---|---|---|---|
| 64 | 796 | 6.2.6 | Sprint 5 | Tạo màn hình báo giá | DONE | UI báo giá nhiều dòng giữ input, gửi/duyệt; API tạo/accept/reject/owner và tổng tiền được test. | frontend/src/components/Operations/QuotesPanel.tsx; frontend/src/routes/_layout/workspace/repairs.tsx; backend/tests/api/routes/test_quotes_api.py |
| 65 | 797 | 6.2.10 | Sprint 5 | Tạo màn hình xác nhận báo giá | DONE | UI báo giá nhiều dòng giữ input, gửi/duyệt; API tạo/accept/reject/owner và tổng tiền được test. | frontend/src/components/Operations/QuotesPanel.tsx; frontend/src/routes/_layout/workspace/repairs.tsx; backend/tests/api/routes/test_quotes_api.py |
| 66 | 806 | 6.2.13 | Sprint 5 | Tạo màn hình tiếp nhận thiết bị | DONE | UI tiếp nhận form và payload; Backend intake tests + integration chain. | frontend/src/routes/_layout/workspace/intake.tsx; backend/tests/api/routes/test_intake_api.py |
| 67 | 807 | 6.2.22 | Sprint 5 | Tạo màn hình phân công kỹ thuật viên | DONE | UI technician mở phiếu được giao; Backend assign/status/diagnosis, ownership và chuỗi nghiệp vụ hoàn chỉnh trên SQLite. | frontend/src/routes/_layout/workspace/repairs.tsx; backend/tests/api/routes/test_repair_orders_api.py; backend/tests/api/routes/test_commerce_workflow.py |
| 68 | 808 | 6.2.30 | Sprint 5 | Tạo màn hình cập nhật trạng thái | DONE | UI technician mở phiếu được giao; Backend assign/status/diagnosis, ownership và chuỗi nghiệp vụ hoàn chỉnh trên SQLite. | frontend/src/routes/_layout/workspace/repairs.tsx; backend/tests/api/routes/test_repair_orders_api.py; backend/tests/api/routes/test_commerce_workflow.py |
| 69 | 795 | 6.2.35 | Sprint 5 | Tạo màn hình chi tiết phiếu sửa | DONE | UI technician mở phiếu được giao; Backend assign/status/diagnosis, ownership và chuỗi nghiệp vụ hoàn chỉnh trên SQLite. | frontend/src/routes/_layout/workspace/repairs.tsx; backend/tests/api/routes/test_repair_orders_api.py; backend/tests/api/routes/test_commerce_workflow.py |
| 70 | 2009 | 6.2.36 | Sprint 5 | Thiết kế UI hoàn chỉnh nhân viên/kỹ thuật viên và báo giá | PARTIAL | UI repair/quotes/intake đã kiểm thử; chưa được nhóm xác nhận đầy đủ thiết kế/wireframe. | frontend/src/components/Operations/; frontend/tests/operations.spec.ts |
| 71 | 809 | 6.2.37 | Sprint 5 | Tạo màn hình quản lý báo giá | DONE | UI báo giá nhiều dòng giữ input, gửi/duyệt; API tạo/accept/reject/owner và tổng tiền được test. | frontend/src/components/Operations/QuotesPanel.tsx; frontend/src/routes/_layout/workspace/repairs.tsx; backend/tests/api/routes/test_quotes_api.py |
| 72 | 810 | 6.2.39 | Sprint 5 | Tạo màn hình quản lý đơn sửa | DONE | UI technician mở phiếu được giao; Backend assign/status/diagnosis, ownership và chuỗi nghiệp vụ hoàn chỉnh trên SQLite. | frontend/src/routes/_layout/workspace/repairs.tsx; backend/tests/api/routes/test_repair_orders_api.py; backend/tests/api/routes/test_commerce_workflow.py |
| 73 | 811 | 6.2.40 | Sprint 5 | Tạo dashboard kỹ thuật viên | DONE | UI dashboard có việc được giao và link kỹ thuật; Backend kiểm tra assigned scope. | frontend/src/routes/_layout/app.tsx; frontend/tests/operations.spec.ts |
| 74 | 813 | 6.2.41 | Sprint 5 | Tạo màn hình danh sách việc cần làm | DONE | UI technician mở phiếu được giao; Backend assign/status/diagnosis, ownership và chuỗi nghiệp vụ hoàn chỉnh trên SQLite. | frontend/src/routes/_layout/workspace/repairs.tsx; backend/tests/api/routes/test_repair_orders_api.py; backend/tests/api/routes/test_commerce_workflow.py |
| 75 | 820 | 6.2.42 | Sprint 5 | Tạo màn hình quản lý đơn sửa | DONE | UI technician mở phiếu được giao; Backend assign/status/diagnosis, ownership và chuỗi nghiệp vụ hoàn chỉnh trên SQLite. | frontend/src/routes/_layout/workspace/repairs.tsx; backend/tests/api/routes/test_repair_orders_api.py; backend/tests/api/routes/test_commerce_workflow.py |
| 76 | 2085 | 6.3.1 | Sprint 5 | Tích hợp đầu-cuối Sprint 5: React ↔ FastAPI ↔ PostgreSQL | PARTIAL | API workflow đã chạy trên SQLite + UI mock; PostgreSQL chỉ đọc schema/catalog và login thật. Chưa chạy browser ghi nghiệp vụ end-to-end vào PostgreSQL test. | backend/tests/api/routes/test_commerce_workflow.py; frontend/tests/; docs/hung-fast-track-progress.md |
| 77 | 2086 | 6.3.2 | Sprint 5 | Kiểm thử acceptance và hồi quy Sprint 5 | PARTIAL | Đã hồi quy các luồng chính; chưa phủ mọi acceptance criterion/biên dữ liệu/role/viewport trong Excel. | docs/hung-fast-track-verification.md |
| 78 | 2088 | 6.3.4 | Sprint 5 | Sửa lỗi frontend theo kết quả kiểm thử Sprint 5 | DONE | Các lỗi phát hiện trong lượt QA đã phân loại/sửa/retest; xem bug log, không có lỗi đỏ còn mở trong bộ test đã chạy. | docs/hung-fast-track-verification.md |
| 79 | 2090 | 6.3.6 | Sprint 5 | Retest, xác minh Definition of Done Sprint 5 | PARTIAL | Đã có retest kỹ thuật; chưa xác nhận toàn bộ Definition of Done của Sprint do E2E PostgreSQL và nghiệm thu nhóm còn thiếu. | docs/hung-fast-track-verification.md |
| 80 | 2077 | 6.4.1 | Sprint 5 | Họp tuần 5 – báo cáo tiến độ, demo và thống nhất việc tiếp theo | BLOCKED | Cần cuộc họp/demo thật và biên bản của thành viên; không thể tự tạo bằng chứng họp. | — |

## Sprint 6

| # | UID | WBS | Sprint | Tên task (nguyên gốc) | Trạng thái | Bằng chứng / phần còn thiếu | File liên quan |
|---:|---:|---|---|---|---|---|---|
| 81 | 780 | 7.2.4 | Sprint 6 | Tạo giao diện quên mật khẩu và đặt lại mật khẩu | PARTIAL | UI mock recovery/reset PASS, API reset tests PASS; gửi/nhận email thực tế qua Mailpit chưa kiểm thử. | frontend/tests/account-flows.spec.ts; frontend/src/routes/recover-password.tsx; frontend/src/routes/reset-password.tsx |
| 82 | 798 | 7.2.9 | Sprint 6 | Tạo màn hình thanh toán | DONE | UI thu tiền → hóa đơn PAID; API issue/payment/history/handover, chống lặp/thu dư/quyền owner; in danh sách qua trình duyệt. | frontend/src/routes/_layout/invoices.tsx; backend/app/services/commerce_service.py; backend/tests/api/routes/test_commerce_workflow.py |
| 83 | 799 | 7.2.14 | Sprint 6 | Tạo màn hình hóa đơn | DONE | UI thu tiền → hóa đơn PAID; API issue/payment/history/handover, chống lặp/thu dư/quyền owner; in danh sách qua trình duyệt. | frontend/src/routes/_layout/invoices.tsx; backend/app/services/commerce_service.py; backend/tests/api/routes/test_commerce_workflow.py |
| 84 | 818 | 7.2.17 | Sprint 6 | Tạo màn hình quản lý tài khoản | DONE | UI superuser tạo role technician, Backend users tests; quyền quản trị tài khoản vẫn theo is_superuser, không nới lỏng. | frontend/src/components/Admin/; frontend/tests/operations.spec.ts |
| 85 | 794 | 7.2.19 | Sprint 6 | Tạo màn hình lịch sử | DONE | appointments.spec: link danh sách, direct/reload detail, hủy xác nhận và đổi giờ; Backend owner + history tests. | frontend/src/routes/_layout/appointments/; frontend/src/routes/_layout/appointments.$appointmentId.tsx; frontend/tests/appointments.spec.ts |
| 86 | 2010 | 7.2.20 | Sprint 6 | Thiết kế UI hoàn chỉnh hóa đơn và ghi nhận thanh toán | PARTIAL | UI thanh toán/hóa đơn dùng component chung, có confirmation; chưa QA in/PDF và mọi viewport riêng của tài chính. | frontend/src/routes/_layout/invoices.tsx |
| 87 | 821 | 7.2.21 | Sprint 6 | Tạo màn hình quản lý thanh toán | DONE | UI thu tiền → hóa đơn PAID; API issue/payment/history/handover, chống lặp/thu dư/quyền owner; in danh sách qua trình duyệt. | frontend/src/routes/_layout/invoices.tsx; backend/app/services/commerce_service.py; backend/tests/api/routes/test_commerce_workflow.py |
| 88 | 2101 | 7.3.1 | Sprint 6 | Tích hợp đầu-cuối Sprint 6: React ↔ FastAPI ↔ PostgreSQL | PARTIAL | API workflow đã chạy trên SQLite + UI mock; PostgreSQL chỉ đọc schema/catalog và login thật. Chưa chạy browser ghi nghiệp vụ end-to-end vào PostgreSQL test. | backend/tests/api/routes/test_commerce_workflow.py; frontend/tests/; docs/hung-fast-track-progress.md |
| 89 | 2102 | 7.3.2 | Sprint 6 | Kiểm thử acceptance và hồi quy Sprint 6 | PARTIAL | Đã hồi quy các luồng chính; chưa phủ mọi acceptance criterion/biên dữ liệu/role/viewport trong Excel. | docs/hung-fast-track-verification.md |
| 90 | 2104 | 7.3.4 | Sprint 6 | Sửa lỗi frontend theo kết quả kiểm thử Sprint 6 | DONE | Các lỗi phát hiện trong lượt QA đã phân loại/sửa/retest; xem bug log, không có lỗi đỏ còn mở trong bộ test đã chạy. | docs/hung-fast-track-verification.md |
| 91 | 2106 | 7.3.6 | Sprint 6 | Retest, xác minh Definition of Done Sprint 6 | PARTIAL | Đã có retest kỹ thuật; chưa xác nhận toàn bộ Definition of Done của Sprint do E2E PostgreSQL và nghiệm thu nhóm còn thiếu. | docs/hung-fast-track-verification.md |
| 92 | 2093 | 7.4.1 | Sprint 6 | Họp tuần 6 – báo cáo tiến độ, demo và thống nhất việc tiếp theo | BLOCKED | Cần cuộc họp/demo thật và biên bản của thành viên; không thể tự tạo bằng chứng họp. | — |

## Sprint 7

| # | UID | WBS | Sprint | Tên task (nguyên gốc) | Trạng thái | Bằng chứng / phần còn thiếu | File liên quan |
|---:|---:|---|---|---|---|---|---|
| 93 | 800 | 8.2.6 | Sprint 7 | Tạo màn hình đánh giá | DONE | UI gửi review, đọc thông báo riêng; Backend ownership/duplicate/status tests. | frontend/src/routes/_layout/reviews.tsx; frontend/src/routes/_layout/notifications.tsx; frontend/tests/operations.spec.ts |
| 94 | 801 | 8.2.11 | Sprint 7 | Tạo màn hình thông báo | DONE | UI gửi review, đọc thông báo riêng; Backend ownership/duplicate/status tests. | frontend/src/routes/_layout/reviews.tsx; frontend/src/routes/_layout/notifications.tsx; frontend/tests/operations.spec.ts |
| 95 | 814 | 8.2.16 | Sprint 7 | Tạo dashboard quản trị | DONE | UI manager báo cáo responsive + service update/disable; Backend revenue từ SUCCESS payments và role tests. | frontend/src/routes/_layout/workspace/reports.tsx; frontend/src/routes/_layout/workspace/services.tsx; backend/tests/api/routes/test_commerce_workflow.py |
| 96 | 815 | 8.2.22 | Sprint 7 | Tạo màn hình quản lý dịch vụ | DONE | UI manager báo cáo responsive + service update/disable; Backend revenue từ SUCCESS payments và role tests. | frontend/src/routes/_layout/workspace/reports.tsx; frontend/src/routes/_layout/workspace/services.tsx; backend/tests/api/routes/test_commerce_workflow.py |
| 97 | 822 | 8.2.27 | Sprint 7 | Tạo màn hình thống kê | DONE | UI manager báo cáo responsive + service update/disable; Backend revenue từ SUCCESS payments và role tests. | frontend/src/routes/_layout/workspace/reports.tsx; frontend/src/routes/_layout/workspace/services.tsx; backend/tests/api/routes/test_commerce_workflow.py |
| 98 | 823 | 8.2.29 | Sprint 7 | Tạo màn hình doanh thu | DONE | UI manager báo cáo responsive + service update/disable; Backend revenue từ SUCCESS payments và role tests. | frontend/src/routes/_layout/workspace/reports.tsx; frontend/src/routes/_layout/workspace/services.tsx; backend/tests/api/routes/test_commerce_workflow.py |
| 99 | 2014 | 8.2.30 | Sprint 7 | Thiết kế UI hoàn chỉnh dashboard, đánh giá và thông báo | PARTIAL | Báo cáo responsive 375/768/1440 và review/notification interactions PASS; chưa audit accessibility toàn bộ sản phẩm. | frontend/tests/operations.spec.ts |
| 100 | 2117 | 8.3.1 | Sprint 7 | Tích hợp đầu-cuối Sprint 7: React ↔ FastAPI ↔ PostgreSQL | PARTIAL | API workflow đã chạy trên SQLite + UI mock; PostgreSQL chỉ đọc schema/catalog và login thật. Chưa chạy browser ghi nghiệp vụ end-to-end vào PostgreSQL test. | backend/tests/api/routes/test_commerce_workflow.py; frontend/tests/; docs/hung-fast-track-progress.md |
| 101 | 828 | 8.3.2 | Sprint 7 | Regression Test | PARTIAL | Đã hồi quy các luồng chính; chưa phủ mọi acceptance criterion/biên dữ liệu/role/viewport trong Excel. | docs/hung-fast-track-verification.md |
| 102 | 826 | 8.2.40 | Sprint 7 | Phân loại Bug | DONE | Bug log mức độ/nguồn/nguyên nhân/kết quả sửa; retest các lỗi routing, mock, quyền và semantic headings. | docs/hung-fast-track-verification.md |
| 103 | 2120 | 8.3.5 | Sprint 7 | Sửa lỗi frontend theo kết quả kiểm thử Sprint 7 | DONE | Các lỗi phát hiện trong lượt QA đã phân loại/sửa/retest; xem bug log, không có lỗi đỏ còn mở trong bộ test đã chạy. | docs/hung-fast-track-verification.md |
| 104 | 829 | 8.3.6 | Sprint 7 | Smoke Test bản demo | PARTIAL | Smoke tự động các luồng UI/API PASS; demo xuyên suốt ghi PostgreSQL với đủ role/data chưa chạy. | docs/hung-fast-track-demo.md |
| 105 | 827 | 8.3.7 | Sprint 7 | Retest Bug đã sửa | DONE | Bug log mức độ/nguồn/nguyên nhân/kết quả sửa; retest các lỗi routing, mock, quyền và semantic headings. | docs/hung-fast-track-verification.md |
| 106 | 830 | 8.2.45 | Sprint 7 | Xác nhận phiên bản Release | BLOCKED | Cần người phụ trách xác nhận release và môi trường triển khai; không tự deploy/push/tag. | docs/hung-fast-track-demo.md |
| 107 | 831 | 8.2.48 | Sprint 7 | Bàn giao frontend | PARTIAL | Đã chuẩn bị hướng dẫn khởi động, kiểm thử, demo, commit, hạn chế; chưa có xác nhận nhận bàn giao từ nhóm. | docs/hung-fast-track-demo.md |
| 108 | 2109 | 8.4.2 | Sprint 7 | Họp tuần 7 – báo cáo tiến độ, demo và thống nhất việc tiếp theo | BLOCKED | Cần cuộc họp/demo thật và biên bản của thành viên; không thể tự tạo bằng chứng họp. | — |

## Cách diễn giải task trùng tên

- UID 803: quản lý trạng thái/ngày giờ lịch hẹn; UID 819: quản lý ca làm việc kỹ thuật viên, tái sử dụng màn technicians. Không tạo màn trùng chức năng chỉ để tăng số file.
- UID 810 và 820: dùng cùng màn phiếu sửa theo quyền của nhân viên/kỹ thuật viên, API vẫn kiểm tra scope theo người dùng.
- UID 792: đặt chỗ nhanh tại hàng chờ bằng queue API thật; lỗi hết chỗ do Backend quyết định, không giả thành công.
- Mỗi task QA/họp/release độc lập với task viết màn hình. Không tự chuyển tất cả sang DONE khi code đã build.
