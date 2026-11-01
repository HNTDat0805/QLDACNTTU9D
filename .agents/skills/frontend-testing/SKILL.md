---
name: frontend-testing
description: Thiết kế, viết và chạy kiểm thử frontend bằng Playwright dựa trên acceptance criteria, với báo cáo kết quả minh bạch.
---

# Kiểm thử frontend

## Khi dùng

Dùng khi viết/rà soát/chạy test frontend, hoặc khi một task thay đổi hành vi người dùng. Đọc `ui-ux-design` để bao phủ accessibility và trạng thái UI; đọc `api-integration` nếu test phụ thuộc API.

## Thiết lập hiện có

- Playwright: `frontend/playwright.config.ts`; test: `frontend/tests/`; lệnh: `cd frontend; bun run test`.
- Config tự chạy Vite nếu không đặt `PLAYWRIGHT_BASE_URL`; dự án Chromium phụ thuộc `tests/auth.setup.ts` và auth state `playwright/.auth/user.json`.
- Test hiện có như `frontend/tests/items.spec.ts` và `login.spec.ts` ưu tiên locator theo role, label và text. Tiếp tục phong cách này; chỉ dùng `data-testid` khi semantic locator không ổn định hoặc không đủ.

## Quy trình QA

1. Chuyển acceptance criteria (tiêu chí chấp nhận: điều kiện người dùng cần thấy hoạt động đúng) thành test case: tiền điều kiện, bước thao tác, kết quả mong đợi và dữ liệu test.
2. Bao phủ luồng thành công, validation/lỗi, quyền truy cập, loading, empty state và hành vi responsive/accessibility liên quan. Không tự khẳng định một API chưa có là hoạt động.
3. Test độc lập: tạo dữ liệu riêng bằng helper/API test đã có khi phù hợp; không phụ thuộc thứ tự test hoặc dữ liệu môi trường không kiểm soát.
4. Chạy lint/test nhỏ nhất đủ bao phủ trước, rồi suite liên quan. Không công bố test pass nếu chưa chạy. Nếu bị chặn (dịch vụ, browser, credential), nêu lệnh đã thử, nguyên nhân và phần chưa xác minh; không lộ biến môi trường.

## Checklist

- [ ] Mỗi test có liên hệ rõ với acceptance criterion.
- [ ] Locator ưu tiên `getByRole`, `getByLabel`, `getByText`; assertion kiểm tra kết quả nhìn thấy được.
- [ ] Test không dùng `waitForTimeout` tùy tiện và không phụ thuộc test khác.
- [ ] Bao phủ success, error/validation và state phù hợp của thay đổi.
- [ ] Đã chạy lệnh, hoặc ghi rõ chưa chạy/bị chặn và lý do.
- [ ] Báo cáo tách biệt: đã chạy–pass/fail, chưa chạy, rủi ro còn lại.

## Ví dụ trong repository

`frontend/tests/items.spec.ts` kiểm tra tạo/sửa/xóa và empty state; `frontend/tests/login.spec.ts` kiểm tra validation, login/logout và route bảo vệ. Các test mới cho lịch hẹn hoặc sửa chữa nên theo cấu trúc này, với acceptance criteria nghiệp vụ đã được cung cấp.
