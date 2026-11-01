# Nghiệm thu UID 767 — Thiết lập layout chung

**WBS:** 2.2.20
**Sprint:** 1
**Ngày ghi nhận:** 27/10/2026

## Phạm vi đã xác minh

- Route công khai `/` hiển thị layout FixCare khi chưa đăng nhập.
- Route bảo vệ `/app` dùng layout có sidebar, header và footer; người chưa đăng nhập được chuyển tới `/login`.
- Đăng nhập thành công chuyển tới `/app`; đăng nhập sai vẫn ở `/login` và hiển thị lỗi API.
- Sidebar trên mobile mở/đóng được; layout được kiểm tra ở 375px, 768px và 1440px.
- Theme sáng/tối hoạt động.
- Điều hướng không đưa người dùng tới các màn hình nghiệp vụ chưa triển khai.
- Navigation sử dụng `UserPublic.role` và `is_superuser` từ Backend; việc ẩn menu không thay thế authorization của Backend.

## Kết quả kiểm thử

| Hạng mục | Lệnh / bằng chứng | Kết quả |
|---|---|---|
| Kiểm thử layout độc lập | `tests/layout-routing.spec.ts` | PASS — 4/4 (mock API cô lập) |
| Xử lý lỗi HTTP hồi quy | `tests/http-error-handling.spec.ts` | PASS — 7/7 (mock API cô lập) |
| Xác thực Playwright | `tests/auth.setup.ts` | PASS — 1/1 (Backend local) |
| Đăng nhập và logout | `tests/login.spec.ts` | PASS — 10/10 (Backend local) |
| TypeScript typecheck | `bunx tsc --noEmit -p tsconfig.json` | PASS |
| Frontend build | `bun run build` | PASS |
| Biome phạm vi UID 767 | `bunx biome check <các file UID 767>` | PASS |

## Giới hạn còn lại

- Các màn hình nghiệp vụ đặt lịch, hàng chờ, báo giá và thanh toán không thuộc UID 767, nên không xuất hiện trong navigation.
- Tài khoản Superuser local đang có `is_superuser=true` nhưng `role=customer`; quyền admin hiện dựa vào `is_superuser`, song dữ liệu role cần được thống nhất trong task Backend/phân quyền riêng.
- `frontend/.env` là file đã được Git theo dõi từ trước UID 767. Nó không thay đổi trong task này, nhưng cần một task Git/security riêng để đánh giá và xử lý theo chính sách repository.
