# Audit 108 task Frontend & QA của Hưng

> Audit gốc ngày 26/10/2026 được giữ lại để đối chiếu. Trạng thái hiện tại sau fast-track ngày 27/10/2026 nằm trong [bảng đủ 108 UID](hung-fast-track-status.md), [tiến độ](hung-fast-track-progress.md) và [bằng chứng kiểm thử](hung-fast-track-verification.md). Các nhận định thiếu code/client bên dưới là tại thời điểm audit gốc, không áp dụng cho mã mới. UID 770 đã xác minh hoàn thành, mã ở commit `486394b`; client tiếp tục được regenerate theo API mới.

## Phạm vi và quy ước bằng chứng

Nguồn task: `docs/project/Task_cua_Hung.xlsx`; nguồn nghiệp vụ: `docs/project/QLDACNTT.docx`; nguồn code: repository tại thời điểm audit. Không có log CI, báo cáo Playwright, ảnh demo hoặc biên bản họp trong repository để xác nhận runtime.

- **Đã xác minh hoàn thành:** có mã đúng nghiệp vụ và bằng chứng test/kiểm tra pass. **Tại thời điểm audit gốc chưa có task đạt ngưỡng này; xem bảng hiện trạng được liên kết phía trên.**
- **Hoàn thành một phần:** có một phần phù hợp, nhưng thiếu phạm vi nghiệp vụ, tích hợp, state UI, AC hoặc kiểm thử.
- **Chưa thực hiện:** không có mã/tài liệu đúng task trong repository.
- **Chưa đủ bằng chứng:** có dấu vết code/config/test, nhưng chưa chứng minh được chức năng chạy hoặc bàn giao đúng AC.

`File` là file hiện có cần tái dùng/đối chiếu, không phải khẳng định task đã làm. `API` dùng `—` khi task không gọi API. Skill: **UX**=`ui-ux-design`, **React**=`react-frontend`, **API**=`api-integration`, **QA**=`frontend-testing`.

## Acceptance criteria và cách kiểm thử chuẩn

| Mã | Acceptance criteria (AC) | Cách kiểm thử (TC) |
|---|---|---|
| AC-CFG | Cấu hình/thư mục hoạt động trong build, không phá cấu trúc hiện có. | TC-CFG: `bun run lint` và `bun run build`; kiểm tra output/route. |
| AC-UI | Màn hình đúng vai trò/nghiệp vụ, mobile-first, có loading/empty/error/success và accessibility cơ bản. | TC-UI: Playwright mở route, dùng role/label, kiểm tra desktop/mobile và keyboard khi phù hợp. |
| AC-FORM | Form có schema, lỗi field, submit/cancel và payload API đúng contract. | TC-FORM: valid/invalid/boundary/cancel qua Playwright. |
| AC-READ | Danh sách/chi tiết lấy dữ liệu thật, có filter/state phù hợp quyền. | TC-READ: mock chỉ trong test hoặc API môi trường test; kiểm tra loading/empty/error/data. |
| AC-MUT | Mutation phản hồi success/error thật, cập nhật cache/UI và bảo vệ hành động nguy hiểm. | TC-MUT: tạo/sửa/hủy/assign, assertion toast + dữ liệu sau refresh. |
| AC-AUTH | Xác thực, phân quyền, hết hạn token và redirect đúng. | TC-AUTH: Playwright logged-in/logged-out/role/invalid token. |
| AC-E2E | Luồng React ↔ FastAPI ↔ PostgreSQL chạy với dữ liệu test độc lập. | TC-E2E: Playwright + API test, lưu command/pass-fail/trace. |
| AC-QA | Test case bám AC; bug/retest có kết quả và bằng chứng. | TC-QA: chạy suite liên quan, ghi pass/fail/blocker. |
| AC-DOC | Có artifact được yêu cầu (biên bản/release/bàn giao) và người chịu trách nhiệm xác nhận. | TC-DOC: review artifact và liên kết bằng chứng. |

## Sprint 1 — PBI-S01

| UID | WBS | Sprint | Tên task (nguyên văn) | Trạng thái xác minh | File liên quan | API phụ thuộc | Skill | AC | Test |
|---:|---|---|---|---|---|---|---|---|---|
| 762 | 2.2.4 | Sprint 1 | Phân tích yêu cầu giao diện | Hoàn thành một phần — DOCX có danh sách màn hình, chưa có AC UI riêng. | `QLDACNTT.docx`, `docs/project/` | — | UX, QA | AC-DOC | TC-DOC |
| 763 | 2.2.9 | Sprint 1 | Khởi tạo project frontend | Chưa đủ bằng chứng — Vite/React config có, chưa có build pass lưu lại. | `frontend/package.json`, `vite.config.ts` | — | React, QA | AC-CFG | TC-CFG |
| 764 | 2.2.13 | Sprint 1 | Thiết lập cấu trúc thư mục frontend | Hoàn thành một phần — routes/components/hooks/client có, cấu trúc domain sửa chữa chưa có. | `frontend/src/{routes,components,hooks,client}` | — | React | AC-CFG | TC-CFG |
| 766 | 2.2.17 | Sprint 1 | Thiết lập component base | Hoàn thành một phần — có `components/ui`, nhưng chưa kiểm tra theo design system nghiệp vụ. | `frontend/src/components/ui/` | — | UX, React, QA | AC-CFG | TC-CFG |
| 767 | 2.2.20 | Sprint 1 | Thiết lập layout chung | Đã xác minh hoàn thành — public layout `/`, authenticated layout `/app`, điều hướng theo quyền an toàn và kiểm thử tích hợp đăng nhập đạt. | `routes/index.tsx`, `routes/_layout.tsx`, `routes/_layout/app.tsx`, `components/Common/`, `components/Sidebar/`, `tests/layout-routing.spec.ts`, `tests/login.spec.ts` | `LoginService`, `UsersService.readUserMe` | UX, React, QA | AC-UI | TC-UI |
| 769 | 2.2.25 | Sprint 1 | Thiết lập form validation | Hoàn thành một phần — RHF/Zod có ở form template, chưa có schema đặt lịch/sửa chữa. | `components/ui/form.tsx`, `routes/login.tsx` | — | React, QA | AC-FORM | TC-FORM |
| 770 | 2.2.30 | Sprint 1 | Thiết lập HTTP client | Đã xác minh hoàn thành — OpenAPI runtime có 52 path, 70 operation, 0 operationId trùng; generated Axios client có 16 service và test xử lý lỗi HTTP đạt 7/7. | `main.tsx`, `src/client/`, `openapi-ts.config.ts`, `tests/http-error-handling.spec.ts` | OpenAPI contract | API, React, QA | AC-CFG | TC-CFG |
| 776 | 2.2.37 | Sprint 1 | Tạo trang danh sách dịch vụ | Chưa thực hiện — Items là code mẫu, không phải Service. | `routes/_layout/items.tsx` (chỉ mẫu) | Service list **thiếu** | UX, React, API, QA | AC-READ | TC-UI |
| 765 | 2.2.43 | Sprint 1 | Thiết lập routing | Hoàn thành một phần — TanStack routes có, chưa có route nghiệp vụ khách hàng. | `routes/`, `routeTree.gen.ts` | — | React, QA | AC-CFG | TC-CFG |
| 768 | 2.2.49 | Sprint 1 | Thiết lập responsive grid | Hoàn thành một phần — Tailwind responsive xuất hiện cục bộ, chưa có grid/system được xác minh. | `index.css`, `_layout.tsx` | — | UX, React, QA | AC-UI | TC-UI |
| 772 | 2.2.54 | Sprint 1 | Tạo trang Landing | Đã xác minh hoàn thành — Landing FixCare tại `/` có hero, giá trị định hướng, quy trình 4 bước, lợi ích theo vai trò và CTA thật; build, typecheck, Biome và Playwright liên quan đạt. | `routes/index.tsx`, `components/landing/`, `tests/landing.spec.ts` | — | UX, React, QA | AC-UI | TC-UI |
| 773 | 2.2.57 | Sprint 1 | Tạo Header | Hoàn thành một phần — header nội bộ có, header công khai/CTA chưa có. | `routes/_layout.tsx` | — | UX, React, QA | AC-UI | TC-UI |
| 774 | 2.2.60 | Sprint 1 | Tạo Footer | Chưa đủ bằng chứng — `Footer.tsx` tồn tại nhưng chưa kiểm tra UI/route. | `components/Common/Footer.tsx` | — | UX, React, QA | AC-UI | TC-UI |
| 775 | 2.2.63 | Sprint 1 | Tạo trang giới thiệu cửa hàng | Chưa thực hiện. | `routes/` | — | UX, React, QA | AC-UI | TC-UI |
| 777 | 2.2.67 | Sprint 1 | Tạo trang chi tiết dịch vụ | Chưa thực hiện. | `routes/` | Service detail **thiếu** | UX, React, API, QA | AC-READ | TC-UI |
| 902 | 2.2.69 | Sprint 1 | Thiết lập CI/CD React và build frontend tự động | Chưa thực hiện — không thấy workflow CI. | `.github/` không có | — | React, QA | AC-CFG | TC-CFG |
| 2024 | 2.3.1 | Sprint 1 | Tích hợp đầu-cuối Sprint 1: React ↔ FastAPI ↔ PostgreSQL | Chưa đủ bằng chứng — có template API/test, không có luồng dịch vụ thật hay log chạy. | `main.tsx`, `tests/` | Service APIs thiếu | React, API, QA | AC-E2E | TC-E2E |
| 2025 | 2.3.2 | Sprint 1 | Kiểm thử acceptance và hồi quy Sprint 1 | Hoàn thành một phần — Playwright template có, chưa có case dịch vụ/landing. | `frontend/tests/` | Service APIs thiếu | QA | AC-QA | TC-QA |
| 2027 | 2.3.4 | Sprint 1 | Sửa lỗi frontend theo kết quả kiểm thử Sprint 1 | Chưa đủ bằng chứng — không có bug report/kết quả test Sprint 1. | `frontend/tests/` | — | UX, React, QA | AC-QA | TC-QA |
| 2029 | 2.3.6 | Sprint 1 | Retest, xác minh Definition of Done Sprint 1 | Chưa đủ bằng chứng — không có DoD/retest record. | `docs/` | — | QA | AC-QA | TC-QA |
| 2016 | 2.4.1 | Sprint 1 | Họp tuần 1 – báo cáo tiến độ, demo và thống nhất việc tiếp theo | Chưa đủ bằng chứng — không có biên bản. | `docs/project/` | — | QA | AC-DOC | TC-DOC |

## Sprint 2 — PBI-S02

| UID | WBS | Sprint | Tên task (nguyên văn) | Trạng thái xác minh | File liên quan | API phụ thuộc | Skill | AC | Test |
|---:|---|---|---|---|---|---|---|---|---|
| 771 | 3.2.3 | Sprint 2 | Thiết lập xử lý token | Hoàn thành một phần — Frontend lưu refresh token, tự refresh một lần khi 401 và thu hồi token khi logout; cần chạy lại toàn bộ suite auth tích hợp để xác minh với Backend thực. | `main.tsx`, `hooks/useAuth.ts`, `tests/http-error-handling.spec.ts` | login, refresh/revoke | React, API, QA | AC-AUTH | TC-AUTH |
| 778 | 3.2.14 | Sprint 2 | Tạo trang đăng ký | Chưa đủ bằng chứng — route/form/API template có, chưa chạy. | `routes/signup.tsx`, `useAuth.ts` | register | UX, React, API, QA | AC-FORM | TC-FORM |
| 779 | 3.2.17 | Sprint 2 | Tạo trang đăng nhập | Chưa đủ bằng chứng — route/form/API template + test có, chưa có result run. | `routes/login.tsx`, `tests/login.spec.ts` | login | UX, React, API, QA | AC-AUTH | TC-AUTH |
| 781 | 3.2.19 | Sprint 2 | Tạo trang hồ sơ cá nhân | Hoàn thành một phần — Settings user template có, chưa điều chỉnh role/ngôn ngữ nghiệp vụ. | `routes/_layout/settings.tsx`, `UserSettings/` | users/me | UX, React, API, QA | AC-FORM | TC-FORM |
| 824 | 3.2.21 | Sprint 2 | Kết nối API đăng ký | Chưa đủ bằng chứng — `UsersService.registerUser` được gọi, chưa chạy. | `hooks/useAuth.ts` | register | API, React, QA | AC-MUT | TC-FORM |
| 825 | 3.2.23 | Sprint 2 | Kết nối API đăng nhập | Chưa đủ bằng chứng — `LoginService.loginAccessToken` được gọi, refresh chưa có UI. | `hooks/useAuth.ts` | login, refresh | API, React, QA | AC-AUTH | TC-AUTH |
| 2039 | 3.3.1 | Sprint 2 | Tích hợp đầu-cuối Sprint 2: React ↔ FastAPI ↔ PostgreSQL | Chưa đủ bằng chứng — mã template không thay bằng E2E evidence. | `main.tsx`, `tests/` | auth/users | React, API, QA | AC-E2E | TC-E2E |
| 2040 | 3.3.2 | Sprint 2 | Kiểm thử acceptance và hồi quy Sprint 2 | Hoàn thành một phần — có test auth template, chưa có log run/AC theo DOCX. | `tests/login.spec.ts`, `sign-up.spec.ts` | auth/users | QA | AC-QA | TC-QA |
| 2042 | 3.3.4 | Sprint 2 | Sửa lỗi frontend theo kết quả kiểm thử Sprint 2 | Chưa đủ bằng chứng. | `frontend/tests/` | — | React, QA | AC-QA | TC-QA |
| 2044 | 3.3.6 | Sprint 2 | Retest, xác minh Definition of Done Sprint 2 | Chưa đủ bằng chứng. | `docs/` | — | QA | AC-QA | TC-QA |
| 2031 | 3.4.1 | Sprint 2 | Họp tuần 2 – báo cáo tiến độ, demo và thống nhất việc tiếp theo | Chưa đủ bằng chứng. | `docs/project/` | — | QA | AC-DOC | TC-DOC |

## Sprint 3 — PBI-S03

| UID | WBS | Sprint | Tên task (nguyên văn) | Trạng thái xác minh | File liên quan | API phụ thuộc | Skill | AC | Test |
|---:|---|---|---|---|---|---|---|---|---|
| 786 | 4.2.4 | Sprint 3 | Tạo giao diện kiểm tra slot trống | Chưa thực hiện — backend có slots nhưng frontend/client không có. | `api/routes/slots.py`, `frontend/routes/` | slots available/check | UX, React, API, QA | AC-READ | TC-UI |
| 782 | 4.2.12 | Sprint 3 | Tạo trang chọn dịch vụ | Chưa thực hiện. | `models.py: Service` | Service list **thiếu** | UX, React, API, QA | AC-READ | TC-UI |
| 783 | 4.2.17 | Sprint 3 | Tạo giao diện chọn ngày | Chưa thực hiện. | `routes/`, `slots.py` | slots available | UX, React, API, QA | AC-FORM | TC-FORM |
| 784 | 4.2.21 | Sprint 3 | Tạo giao diện chọn giờ | Chưa thực hiện. | `routes/`, `slots.py` | slots/check | UX, React, API, QA | AC-FORM | TC-FORM |
| 785 | 4.2.24 | Sprint 3 | Tạo giao diện chọn kỹ thuật viên | Chưa thực hiện. | `technicians.py` | technicians list | UX, React, API, QA | AC-READ | TC-UI |
| 788 | 4.2.25 | Sprint 3 | Tạo màn hình xác nhận lịch | Chưa thực hiện. | `appointments.py` | appointment create | UX, React, API, QA | AC-MUT | TC-FORM |
| 787 | 4.2.26 | Sprint 3 | Tạo form đặt lịch | Chưa thực hiện. | `models.py`, `appointments.py` | booking create, slots, services | UX, React, API, QA | AC-FORM | TC-FORM |
| 789 | 4.2.28 | Sprint 3 | Tạo màn hình lịch đã đặt | Chưa thực hiện. | `appointments.py` | appointment history/lookup | UX, React, API, QA | AC-READ | TC-UI |
| 790 | 4.2.29 | Sprint 3 | Tạo chức năng đổi lịch | Chưa thực hiện. | `appointments.py` | appointment update, slots | UX, React, API, QA | AC-MUT | TC-MUT |
| 791 | 4.2.31 | Sprint 3 | Tạo chức năng hủy lịch | Chưa thực hiện. | `appointments.py` | appointment cancel | UX, React, API, QA | AC-MUT | TC-MUT |
| 2054 | 4.3.1 | Sprint 3 | Tích hợp đầu-cuối Sprint 3: React ↔ FastAPI ↔ PostgreSQL | Chưa thực hiện — chưa có frontend booking. | `appointments.py`, `frontend/` | booking stack | React, API, QA | AC-E2E | TC-E2E |
| 2055 | 4.3.2 | Sprint 3 | Kiểm thử acceptance và hồi quy Sprint 3 | Chưa thực hiện — không có booking test. | `frontend/tests/` | booking stack | QA | AC-QA | TC-QA |
| 2057 | 4.3.4 | Sprint 3 | Sửa lỗi frontend theo kết quả kiểm thử Sprint 3 | Chưa đủ bằng chứng. | `frontend/tests/` | — | React, QA | AC-QA | TC-QA |
| 2059 | 4.3.6 | Sprint 3 | Retest, xác minh Definition of Done Sprint 3 | Chưa đủ bằng chứng. | `docs/` | — | QA | AC-QA | TC-QA |
| 2046 | 4.4.1 | Sprint 3 | Họp tuần 3 – báo cáo tiến độ, demo và thống nhất việc tiếp theo | Chưa đủ bằng chứng. | `docs/project/` | — | QA | AC-DOC | TC-DOC |

## Sprint 4 — PBI-S04

| UID | WBS | Sprint | Tên task (nguyên văn) | Trạng thái xác minh | File liên quan | API phụ thuộc | Skill | AC | Test |
|---:|---|---|---|---|---|---|---|---|---|
| 804 | 5.2.4 | Sprint 4 | Tạo màn hình danh sách lịch hẹn | Chưa thực hiện — backend API có, frontend route không có. | `appointments.py`, `DataTable.tsx` | appointments list/history | UX, React, API, QA | AC-READ | TC-UI |
| 793 | 5.2.10 | Sprint 4 | Tạo màn hình hàng chờ | Chưa thực hiện. | `queue.py`, `DataTable.tsx` | queue list/add/update | UX, React, API, QA | AC-READ | TC-UI |
| 802 | 5.2.14 | Sprint 4 | Tạo dashboard nhân viên | Chưa thực hiện. | `routes/_layout/index.tsx` (template) | appointments/queue aggregates | UX, React, API, QA | AC-READ | TC-UI |
| 803 | 5.2.18 | Sprint 4 | Tạo màn hình quản lý lịch | Chưa thực hiện. | `appointments.py` | appointments update/confirm/cancel | UX, React, API, QA | AC-MUT | TC-MUT |
| 805 | 5.2.22 | Sprint 4 | Tạo màn hình chi tiết lịch hẹn | Chưa thực hiện. | `appointments.py` | appointment detail | UX, React, API, QA | AC-READ | TC-UI |
| 812 | 5.2.24 | Sprint 4 | Tạo màn hình lịch làm việc kỹ thuật viên | Chưa thực hiện. | `work_schedules.py` | work schedules CRUD | UX, React, API, QA | AC-READ | TC-UI |
| 792 | 5.2.28 | Sprint 4 | Tạo màn hình đặt chỗ | Chưa thực hiện. | `queue.py` | queue add/status | UX, React, API, QA | AC-MUT | TC-FORM |
| 2008 | 5.2.29 | Sprint 4 | Thiết kế UI hoàn chỉnh hàng chờ và quản lý lịch từ wireframe | Chưa thực hiện — không có wireframe artifact/frontend domain UI. | `QLDACNTT.docx`, `routes/` | queue/appointments | UX, React, QA | AC-UI | TC-UI |
| 816 | 5.2.30 | Sprint 4 | Tạo màn hình quản lý kỹ thuật viên | Chưa thực hiện. | `technicians.py`, `DataTable.tsx` | technicians CRUD/status | UX, React, API, QA | AC-MUT | TC-MUT |
| 817 | 5.2.32 | Sprint 4 | Tạo màn hình quản lý khách hàng | Chưa thực hiện. | `customers.py`, `DataTable.tsx` | customers CRUD | UX, React, API, QA | AC-MUT | TC-MUT |
| 819 | 5.2.33 | Sprint 4 | Tạo màn hình quản lý lịch | Chưa thực hiện — trùng tên UID 803, cần PM làm rõ phạm vi (lịch hẹn hay lịch làm việc). | `appointments.py`, `work_schedules.py` | cần làm rõ | UX, React, API, QA | AC-READ | TC-UI |
| 2069 | 5.3.1 | Sprint 4 | Tích hợp đầu-cuối Sprint 4: React ↔ FastAPI ↔ PostgreSQL | Chưa thực hiện. | `frontend/`, APIs Sprint 4 | appointments/queue/etc. | React, API, QA | AC-E2E | TC-E2E |
| 2070 | 5.3.2 | Sprint 4 | Kiểm thử acceptance và hồi quy Sprint 4 | Chưa thực hiện. | `frontend/tests/` | APIs Sprint 4 | QA | AC-QA | TC-QA |
| 2072 | 5.3.4 | Sprint 4 | Sửa lỗi frontend theo kết quả kiểm thử Sprint 4 | Chưa đủ bằng chứng. | `frontend/tests/` | — | React, QA | AC-QA | TC-QA |
| 2074 | 5.3.6 | Sprint 4 | Retest, xác minh Definition of Done Sprint 4 | Chưa đủ bằng chứng. | `docs/` | — | QA | AC-QA | TC-QA |
| 2061 | 5.4.1 | Sprint 4 | Họp tuần 4 – báo cáo tiến độ, demo và thống nhất việc tiếp theo | Chưa đủ bằng chứng. | `docs/project/` | — | QA | AC-DOC | TC-DOC |

## Sprint 5 — PBI-S05

| UID | WBS | Sprint | Tên task (nguyên văn) | Trạng thái xác minh | File liên quan | API phụ thuộc | Skill | AC | Test |
|---:|---|---|---|---|---|---|---|---|---|
| 796 | 6.2.6 | Sprint 5 | Tạo màn hình báo giá | Chưa thực hiện. | `quotes.py`, `models.py` | quote create; list/detail cần xác minh | UX, React, API, QA | AC-MUT | TC-FORM |
| 797 | 6.2.10 | Sprint 5 | Tạo màn hình xác nhận báo giá | Chưa thực hiện. | `quotes.py` | quote accept/approve | UX, React, API, QA | AC-MUT | TC-MUT |
| 806 | 6.2.13 | Sprint 5 | Tạo màn hình tiếp nhận thiết bị | Chưa thực hiện. | `intake.py`, `devices.py` | intake create; device read/create cần xác minh | UX, React, API, QA | AC-FORM | TC-FORM |
| 807 | 6.2.22 | Sprint 5 | Tạo màn hình phân công kỹ thuật viên | Chưa thực hiện. | `repair_orders.py`, `appointments.py` | assign technician | UX, React, API, QA | AC-MUT | TC-MUT |
| 808 | 6.2.30 | Sprint 5 | Tạo màn hình cập nhật trạng thái | Chưa thực hiện. | `repair_orders.py` | repair status update | UX, React, API, QA | AC-MUT | TC-MUT |
| 795 | 6.2.35 | Sprint 5 | Tạo màn hình chi tiết phiếu sửa | Chưa thực hiện — read/detail API repair order chưa thấy. | `repair_orders.py` | repair detail **thiếu/xác minh** | UX, React, API, QA | AC-READ | TC-UI |
| 2009 | 6.2.36 | Sprint 5 | Thiết kế UI hoàn chỉnh nhân viên/kỹ thuật viên và báo giá | Chưa thực hiện. | `routes/`, `components/ui/` | repair/quote APIs | UX, React, QA | AC-UI | TC-UI |
| 809 | 6.2.37 | Sprint 5 | Tạo màn hình quản lý báo giá | Chưa thực hiện — quote list/detail chưa thấy router. | `quotes.py`, `DataTable.tsx` | quote list/detail **thiếu** | UX, React, API, QA | AC-READ | TC-UI |
| 810 | 6.2.39 | Sprint 5 | Tạo màn hình quản lý đơn sửa | Chưa thực hiện — repair list/detail chưa thấy router. | `repair_orders.py`, `DataTable.tsx` | repair list/detail **thiếu** | UX, React, API, QA | AC-READ | TC-UI |
| 811 | 6.2.40 | Sprint 5 | Tạo dashboard kỹ thuật viên | Chưa thực hiện. | `work_schedules.py` | assigned repair/work schedule queries cần xác minh | UX, React, API, QA | AC-READ | TC-UI |
| 813 | 6.2.41 | Sprint 5 | Tạo màn hình danh sách việc cần làm | Chưa thực hiện. | `repair_orders.py` | assigned repair list **thiếu** | UX, React, API, QA | AC-READ | TC-UI |
| 820 | 6.2.42 | Sprint 5 | Tạo màn hình quản lý đơn sửa | Chưa thực hiện — trùng tên UID 810, cần PM làm rõ phạm vi. | `repair_orders.py` | repair list/detail **thiếu** | UX, React, API, QA | AC-READ | TC-UI |
| 2085 | 6.3.1 | Sprint 5 | Tích hợp đầu-cuối Sprint 5: React ↔ FastAPI ↔ PostgreSQL | Chưa thực hiện. | `frontend/`, APIs Sprint 5 | intake/quote/repair | React, API, QA | AC-E2E | TC-E2E |
| 2086 | 6.3.2 | Sprint 5 | Kiểm thử acceptance và hồi quy Sprint 5 | Chưa thực hiện. | `frontend/tests/` | APIs Sprint 5 | QA | AC-QA | TC-QA |
| 2088 | 6.3.4 | Sprint 5 | Sửa lỗi frontend theo kết quả kiểm thử Sprint 5 | Chưa đủ bằng chứng. | `frontend/tests/` | — | React, QA | AC-QA | TC-QA |
| 2090 | 6.3.6 | Sprint 5 | Retest, xác minh Definition of Done Sprint 5 | Chưa đủ bằng chứng. | `docs/` | — | QA | AC-QA | TC-QA |
| 2077 | 6.4.1 | Sprint 5 | Họp tuần 5 – báo cáo tiến độ, demo và thống nhất việc tiếp theo | Chưa đủ bằng chứng. | `docs/project/` | — | QA | AC-DOC | TC-DOC |

## Sprint 6 — PBI-S06

| UID | WBS | Sprint | Tên task (nguyên văn) | Trạng thái xác minh | File liên quan | API phụ thuộc | Skill | AC | Test |
|---:|---|---|---|---|---|---|---|---|---|
| 780 | 7.2.4 | Sprint 6 | Tạo giao diện quên mật khẩu và đặt lại mật khẩu | Chưa đủ bằng chứng — routes/API template có, không có runtime result. | `recover-password.tsx`, `reset-password.tsx` | recover/reset password | UX, React, API, QA | AC-FORM | TC-FORM |
| 798 | 7.2.9 | Sprint 6 | Tạo màn hình thanh toán | Chưa thực hiện. | `models.py: Payment` | payment API **thiếu** | UX, React, API, QA | AC-FORM | TC-FORM |
| 799 | 7.2.14 | Sprint 6 | Tạo màn hình hóa đơn | Chưa thực hiện. | `models.py: Invoice` | invoice API **thiếu** | UX, React, API, QA | AC-READ | TC-UI |
| 818 | 7.2.17 | Sprint 6 | Tạo màn hình quản lý tài khoản | Hoàn thành một phần — Users admin/settings template có, chưa phải role/account domain. | `routes/_layout/admin.tsx`, `UserSettings/` | users CRUD | UX, React, API, QA | AC-MUT | TC-MUT |
| 794 | 7.2.19 | Sprint 6 | Tạo màn hình lịch sử | Chưa thực hiện — history endpoint liên quan appointments nhưng không có UI. | `appointments.py` | appointment/repair history | UX, React, API, QA | AC-READ | TC-UI |
| 2010 | 7.2.20 | Sprint 6 | Thiết kế UI hoàn chỉnh hóa đơn và ghi nhận thanh toán | Chưa thực hiện. | `components/ui/` | payment/invoice **thiếu** | UX, React, QA | AC-UI | TC-UI |
| 821 | 7.2.21 | Sprint 6 | Tạo màn hình quản lý thanh toán | Chưa thực hiện. | `models.py: Payment`, `DataTable.tsx` | payment API **thiếu** | UX, React, API, QA | AC-MUT | TC-MUT |
| 2101 | 7.3.1 | Sprint 6 | Tích hợp đầu-cuối Sprint 6: React ↔ FastAPI ↔ PostgreSQL | Chưa thực hiện. | `frontend/` | payment/invoice/history | React, API, QA | AC-E2E | TC-E2E |
| 2102 | 7.3.2 | Sprint 6 | Kiểm thử acceptance và hồi quy Sprint 6 | Chưa thực hiện. | `frontend/tests/` | APIs Sprint 6 | QA | AC-QA | TC-QA |
| 2104 | 7.3.4 | Sprint 6 | Sửa lỗi frontend theo kết quả kiểm thử Sprint 6 | Chưa đủ bằng chứng. | `frontend/tests/` | — | React, QA | AC-QA | TC-QA |
| 2106 | 7.3.6 | Sprint 6 | Retest, xác minh Definition of Done Sprint 6 | Chưa đủ bằng chứng. | `docs/` | — | QA | AC-QA | TC-QA |
| 2093 | 7.4.1 | Sprint 6 | Họp tuần 6 – báo cáo tiến độ, demo và thống nhất việc tiếp theo | Chưa đủ bằng chứng. | `docs/project/` | — | QA | AC-DOC | TC-DOC |

## Sprint 7 — PBI-S07

| UID | WBS | Sprint | Tên task (nguyên văn) | Trạng thái xác minh | File liên quan | API phụ thuộc | Skill | AC | Test |
|---:|---|---|---|---|---|---|---|---|---|
| 800 | 8.2.6 | Sprint 7 | Tạo màn hình đánh giá | Chưa thực hiện. | `models.py: Review` | review API **thiếu** | UX, React, API, QA | AC-FORM | TC-FORM |
| 801 | 8.2.11 | Sprint 7 | Tạo màn hình thông báo | Chưa thực hiện. | `models.py: Notification` | notification API **thiếu** | UX, React, API, QA | AC-READ | TC-UI |
| 814 | 8.2.16 | Sprint 7 | Tạo dashboard quản trị | Chưa thực hiện — admin route chỉ quản lý Users template, không có dashboard. | `routes/_layout/admin.tsx` | statistics API **thiếu** | UX, React, API, QA | AC-READ | TC-UI |
| 815 | 8.2.22 | Sprint 7 | Tạo màn hình quản lý dịch vụ | Chưa thực hiện. | `models.py: Service`, `DataTable.tsx` | service CRUD **thiếu** | UX, React, API, QA | AC-MUT | TC-MUT |
| 822 | 8.2.27 | Sprint 7 | Tạo màn hình thống kê | Chưa thực hiện. | `routes/` | statistics API **thiếu** | UX, React, API, QA | AC-READ | TC-UI |
| 823 | 8.2.29 | Sprint 7 | Tạo màn hình doanh thu | Chưa thực hiện. | `models.py`, `routes/` | revenue API **thiếu** | UX, React, API, QA | AC-READ | TC-UI |
| 2014 | 8.2.30 | Sprint 7 | Thiết kế UI hoàn chỉnh dashboard, đánh giá và thông báo | Chưa thực hiện. | `components/ui/`, `routes/` | statistics/review/notification **thiếu** | UX, React, QA | AC-UI | TC-UI |
| 2117 | 8.3.1 | Sprint 7 | Tích hợp đầu-cuối Sprint 7: React ↔ FastAPI ↔ PostgreSQL | Chưa thực hiện. | `frontend/` | APIs Sprint 7 thiếu | React, API, QA | AC-E2E | TC-E2E |
| 828 | 8.3.2 | Sprint 7 | Regression Test | Hoàn thành một phần — Playwright base suite có, không có domain regression run/evidence. | `frontend/tests/` | tất cả API demo | QA | AC-QA | TC-QA |
| 826 | 8.2.40 | Sprint 7 | Phân loại Bug | Chưa đủ bằng chứng — không có bug log/Pareto hiện hành. | `docs/project/QLDACNTT.docx` | — | QA | AC-DOC | TC-DOC |
| 2120 | 8.3.5 | Sprint 7 | Sửa lỗi frontend theo kết quả kiểm thử Sprint 7 | Chưa đủ bằng chứng. | `frontend/tests/` | — | React, QA | AC-QA | TC-QA |
| 829 | 8.3.6 | Sprint 7 | Smoke Test bản demo | Chưa đủ bằng chứng — không có demo deployed/log smoke test. | `playwright.config.ts` | demo APIs | QA | AC-QA | TC-QA |
| 827 | 8.3.7 | Sprint 7 | Retest Bug đã sửa | Chưa đủ bằng chứng — thiếu bug/retest record. | `frontend/tests/` | — | QA | AC-QA | TC-QA |
| 830 | 8.2.45 | Sprint 7 | Xác nhận phiên bản Release | Chưa đủ bằng chứng — không thấy release/tag/CI artifact. | `package.json`, repository metadata | — | QA | AC-DOC | TC-DOC |
| 831 | 8.2.48 | Sprint 7 | Bàn giao frontend | Chưa đủ bằng chứng — thiếu hướng dẫn/bản build/biên bản bàn giao theo task. | `frontend/README.md`, `docs/` | — | React, QA | AC-DOC | TC-DOC |
| 2109 | 8.4.2 | Sprint 7 | Họp tuần 7 – báo cáo tiến độ, demo và thống nhất việc tiếp theo | Chưa đủ bằng chứng. | `docs/project/` | — | QA | AC-DOC | TC-DOC |

## Vấn đề cần làm rõ với nhóm

1. UID 803 và 819 đều tên **Tạo màn hình quản lý lịch**; cần xác định một task là lịch hẹn và task còn lại là lịch làm việc.
2. UID 810 và 820 đều tên **Tạo màn hình quản lý đơn sửa**; cần tách phạm vi (nhân viên/quản trị hay list/detail) trước khi code.
3. API service/payment/invoice/review/notification/statistics phải có OpenAPI contract trước khi frontend nhận task tương ứng.
4. Chỉ thay trạng thái audit sau khi lưu link kết quả test, trace/screenshot hoặc báo cáo kiểm tra thủ công có môi trường/ngày chạy.
