---
name: ui-ux-design
description: Thiết kế hoặc rà soát giao diện React cho hệ thống sửa điện thoại, ưu tiên mobile-first, accessibility và tái sử dụng Tailwind/component hiện có.
---

# UI/UX cho cửa hàng sửa điện thoại

## Khi dùng

Dùng trước khi tạo hoặc thay đổi màn hình, luồng đặt lịch, tiếp nhận máy, báo giá, hàng đợi hoặc phiếu sửa. Không dùng để tự thay đổi backend, dữ liệu, Docker hay dependency.

## Bối cảnh dự án

- Stylesheet và design tokens nằm tại `frontend/src/index.css`: Tailwind CSS v4 dùng token CSS (`--primary`, `--background`, `--radius`), hỗ trợ dark mode.
- Ưu tiên component có sẵn ở `frontend/src/components/ui/` (Button, Input, Form, Card, Dialog, Select, Skeleton, Alert, Sheet, Sidebar…) và `frontend/src/components/Common/`.
- Biểu tượng dùng `lucide-react`; không thêm thư viện UI chỉ để thay một component sẵn có.

## Cách thiết kế

1. Trước khi sửa, nêu mục tiêu, màn hình/luồng, file dự kiến sửa và lý do. Đọc component tương tự trước để tái sử dụng nhất quán.
2. Thiết kế mobile-first: nội dung quan trọng và CTA (nút hành động chính) xuất hiện sớm; vùng bấm tối thiểu dễ thao tác; dùng breakpoint Tailwind để mở rộng cho tablet/desktop, không chỉ thu nhỏ giao diện desktop.
3. Với ngữ cảnh sửa điện thoại, làm nổi rõ trạng thái đơn, lịch hẹn, giá và hành động tiếp theo; tránh màu đơn lẻ là cách duy nhất truyền đạt trạng thái.
4. Bảo đảm accessibility (khả năng dùng được với bàn phím, trình đọc màn hình và người có nhu cầu hỗ trợ): dùng phần tử HTML đúng nghĩa, label liên kết input, focus nhìn thấy được, tương phản đủ rõ, thứ tự tab hợp lý, dialog có tiêu đề/mô tả.
5. Tái sử dụng token/Tailwind class và variant component. Chỉ bổ sung token vào `index.css` khi một giá trị lặp lại có ý nghĩa toàn hệ thống; không hard-code bảng màu rời rạc trong nhiều component.

## Trạng thái bắt buộc của màn hình dữ liệu

Thiết kế đầy đủ các trạng thái, phù hợp khả năng API thật:

- loading: dùng `Skeleton` hoặc pending component như `components/Pending/PendingItems.tsx`;
- empty: giải thích chưa có dữ liệu và CTA đúng quyền;
- error: thông báo dễ hiểu, giữ ngữ cảnh và có cách thử lại khi khả thi;
- success: xác nhận hành động bằng `sonner`/toast, sau đó cập nhật dữ liệu hiển thị.

Không dựng dữ liệu giả như thể API đã hoạt động. Nếu API chưa có, hiển thị UI trung thực hoặc dừng để xác nhận phạm vi.

## Checklist trước bàn giao

- [ ] Đã kiểm tra màn hình ở viewport mobile và desktop.
- [ ] Dùng token/Tailwind và component có sẵn thay vì tạo bản sao.
- [ ] Có loading, empty, error, success phù hợp.
- [ ] Form có label, lỗi cụ thể, focus và thao tác bàn phím hoạt động.
- [ ] Màu sắc không là tín hiệu trạng thái duy nhất; văn bản/biểu tượng có nghĩa.
- [ ] Đã nêu component, props, state và luồng dữ liệu thay đổi sau khi sửa.

## Ví dụ trong repository

Trang `frontend/src/routes/_layout/items.tsx` đã tách loading qua `Suspense`/`PendingItems` và empty state. Khi xây màn hình lịch hẹn, áp dụng cùng cấu trúc nhưng dùng component UI hiện có và nội dung phù hợp nghiệp vụ sửa điện thoại.
