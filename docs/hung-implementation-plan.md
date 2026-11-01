# Kế hoạch triển khai Frontend & QA của Hưng

> Cập nhật 27/10/2026: kế hoạch gốc dưới đây được giữ nguyên cho lịch sử. Nhóm B–E đã được triển khai và kiểm thử theo [tiến độ hiện tại](hung-fast-track-progress.md); xem [108 UID hiện trạng](hung-fast-track-status.md). Nhận định client/API thiếu trong kế hoạch gốc đã được xử lý, không phải blocker hiện tại.

> Lập ngày 26/10/2026 từ `docs/project/Task_cua_Hung.xlsx`, `docs/project/QLDACNTT.docx`, `AGENTS.md` và mã nguồn hiện tại. Đây là kế hoạch, không phải bằng chứng đã hoàn thành chức năng.

## Cách đọc kế hoạch

- **Component** là khối giao diện có thể tái sử dụng, ví dụ Button hoặc bảng dữ liệu.
- **Route** là đường dẫn mở một màn hình, ví dụ `/login`.
- **Hook** là hàm React tái sử dụng logic như gọi API hoặc đăng nhập.
- **API/endpoint** là điểm giao tiếp giữa frontend và backend, ví dụ `GET /appointments`.
- **Dependency** là việc phải có trước khi một việc khác hoạt động đúng.
- **Acceptance criteria (AC)** là điều kiện quan sát được để chấp nhận task hoàn thành.
- **Test case** là kịch bản kiểm thử có bước thực hiện và kết quả mong đợi.

## Kết luận ưu tiên cho demo

Demo tối thiểu nên đi theo một câu chuyện đầy đủ: khách chọn dịch vụ và giờ trống → đặt lịch → nhân viên thấy/xác nhận lịch → tiếp nhận thiết bị → tạo báo giá → kỹ thuật viên cập nhật trạng thái. Các màn hình thanh toán, doanh thu, đánh giá và thông báo là ưu tiên sau.

**Blocker lớn nhất:** `frontend/src/client/` chỉ sinh service cho Users, Login, Items, Private và Utils, trong khi backend đã có appointments, slots, customers, technicians, queue, intake, quotes, devices, repair orders và work schedules. Không được đoán service; phải xác minh OpenAPI rồi sinh lại client trước khi tích hợp.

## Thứ tự theo dependency

1. Xác minh URL OpenAPI đang phục vụ, các quyền và response; đối chiếu với `backend/app/main.py`, sau đó đề nghị duyệt sinh lại client (UID 770).
2. Chuẩn hóa vỏ giao diện (token, layout công khai/nội bộ, responsive grid) và giữ component có sẵn (UID 766, 767, 768, 765).
3. Làm luồng demo đặt lịch: slot → dịch vụ → ngày/giờ → kỹ thuật viên → xác nhận → tạo/xem/đổi/hủy lịch (UID 786, 782–791). Cần backend bổ sung API dịch vụ.
4. Làm nhân viên: danh sách/chi tiết lịch, hàng chờ, khách hàng, kỹ thuật viên, tiếp nhận và phân công (UID 804, 793, 805, 812, 816, 817, 806–808).
5. Làm báo giá và phiếu sửa/kỹ thuật viên (UID 796, 797, 795, 809–813).
6. Hoàn thiện QA từng sprint bằng Playwright theo AC, sau đó regression/smoke test; chỉ đánh dấu Done khi có kết quả chạy lưu được.
7. Chỉ sau demo cốt lõi mới làm thanh toán/hóa đơn, đánh giá, thông báo và báo cáo (Sprint 6–7).

## Thiết kế giao diện thống nhất

Sử dụng token trong `frontend/src/index.css`, Tailwind CSS v4 và component ở `frontend/src/components/ui/`. Giao diện mobile-first, dùng các trạng thái rõ ràng: loading (Skeleton), empty, error có thử lại, success qua Sonner toast.

| Vai trò | Điều hướng và màn hình ưu tiên | Quy tắc UI |
|---|---|---|
| Khách hàng | Trang chủ, dịch vụ, đặt lịch, lịch đã đặt, tra cứu/sửa/hủy | CTA “Đặt lịch” nổi bật; wizard theo bước; hiển thị giá và trạng thái bằng chữ lẫn màu. |
| Nhân viên | Dashboard, lịch hẹn, hàng chờ, tiếp nhận, khách hàng | Bảng có lọc/trạng thái; thao tác nguy hiểm trong Dialog xác nhận. |
| Kỹ thuật viên | Việc cần làm, lịch làm việc, chi tiết phiếu sửa, cập nhật trạng thái | Ưu tiên công việc hiện tại, deadline và lịch sử sửa chữa. |
| Quản trị viên | Tài khoản, kỹ thuật viên, dịch vụ, báo cáo | Phân quyền route, bảng dữ liệu, empty/error state và audit-friendly actions. |

## Kế hoạch theo 7 Sprint

### Sprint 1 — nền tảng và giao diện công khai

Giữ thứ tự Excel: 762, 763, 764, 766, 767, 769, 770, 776, 765, 768, 772, 773, 774, 775, 777, 902, 2024, 2025, 2027, 2029, 2016. Có nền tảng template, nhưng chưa có landing/dịch vụ thực tế. Ưu tiên xử lý mismatch API trước màn hình dịch vụ; API dịch vụ hiện chưa có router để tích hợp.

### Sprint 2 — xác thực và hồ sơ

Giữ thứ tự Excel: 771, 778, 779, 781, 824, 825, 2039, 2040, 2042, 2044, 2031. Các route/login form/API template có mã; chưa có bằng chứng chạy. Phải kiểm tra refresh/revoke token và quyền role trước demo nội bộ.

### Sprint 3 — khách đặt lịch

Giữ thứ tự Excel: 786, 782, 783, 784, 785, 788, 787, 789, 790, 791, 2054, 2055, 2057, 2059, 2046. Backend có slots và appointments, nhưng frontend chưa có route/domain client. Cần làm sau UID 770 và API dịch vụ.

### Sprint 4 — vận hành lịch hẹn

Giữ thứ tự Excel: 804, 793, 802, 803, 805, 812, 792, 2008, 816, 817, 819, 2069, 2070, 2072, 2074, 2061. Backend có nhiều API nền nhưng frontend chưa tích hợp. Bắt đầu từ lịch hẹn và hàng chờ để demo được luồng nhân viên.

### Sprint 5 — tiếp nhận, báo giá, sửa chữa

Giữ thứ tự Excel: 796, 797, 806, 807, 808, 795, 2009, 809, 810, 811, 813, 820, 2085, 2086, 2088, 2090, 2077. Backend có create/accept quote, intake, assign/update repair status; thiếu/list-detail endpoints cần xác minh hoặc bổ sung.

### Sprint 6 — hậu mãi và tài chính

Giữ thứ tự Excel: 780, 798, 799, 818, 794, 2010, 821, 2101, 2102, 2104, 2106, 2093. Quên/đặt lại mật khẩu template đã có mã; payment/invoice/history chưa có router frontend hoặc backend được xác minh.

### Sprint 7 — quản trị, chất lượng và release

Giữ thứ tự Excel: 800, 801, 814, 815, 822, 823, 2014, 2117, 828, 826, 2120, 829, 827, 830, 831, 2109. Chỉ làm dashboard/báo cáo sau luồng demo. Không có bằng chứng release hay kết quả regression/smoke test hiện tại.

## Code có thể tái sử dụng

| Mục đích | Tái sử dụng | Lưu ý |
|---|---|---|
| Shell đăng nhập | `components/Common/AuthLayout.tsx`, `routes/login.tsx`, `signup.tsx` | Đổi nội dung/ngôn ngữ theo nghiệp vụ, không coi là màn hình khách hàng hoàn chỉnh. |
| Form | `components/ui/form.tsx`, Input, Select, `react-hook-form`, Zod | Tạo schema theo payload API thật. |
| Bảng/list | `components/Common/DataTable.tsx`, `components/ui/table.tsx`, pagination | Dùng cho lịch hẹn/khách hàng/kỹ thuật viên sau khi có type generated. |
| Dialog xác nhận | Dialog, Alert, `DeleteConfirmation.tsx` | Áp dụng cho hủy lịch, đổi trạng thái, xóa dữ liệu. |
| Data state | TanStack Query, `PendingItems.tsx`, `ErrorComponent.tsx`, Sonner | Tạo pending domain-specific thay vì copy Items. |
| Layout nội bộ | `_layout.tsx`, Sidebar, Footer | Cần cấu hình menu theo role; layout hiện là template. |
| E2E test | Playwright config, `auth.setup.ts`, test locator pattern | Tạo fixture/domain data độc lập; test hiện tại chưa bao phủ nghiệp vụ sửa điện thoại. |

## Tiêu chuẩn “đã xác minh hoàn thành”

Một task chỉ được dùng trạng thái này khi có: (1) mã đúng nghiệp vụ, (2) AC được kiểm tra trên UI/API thật, (3) test case hoặc kiểm tra thủ công có kết quả pass ghi rõ ngày/môi trường. Hiện repository không có báo cáo chạy test hay minh chứng demo, nên audit không tự gán trạng thái đó.
