---
name: react-frontend
description: Phát triển giao diện frontend bằng React 19, TypeScript, TanStack Router/Query, React Hook Form và Zod theo cấu trúc repository.
---

# React frontend

## Khi dùng

Dùng cho một thay đổi frontend nhỏ: route, component, form, state, truy vấn hoặc mutation. Đọc thêm `ui-ux-design` cho thay đổi giao diện và `api-integration` khi gọi API. Không chỉnh file generated, backend, dependency hoặc hạ tầng nếu chưa được phê duyệt.

## Cấu trúc thực tế

- Route file-based ở `frontend/src/routes/`; Vite tự tạo `routeTree.gen.ts`, không sửa file này thủ công.
- Entry point `frontend/src/main.tsx` đã cung cấp `QueryClientProvider`, router, theme và toast.
- Component dùng chung: `frontend/src/components/ui/`, domain component: `frontend/src/components/<Domain>/`, hooks: `frontend/src/hooks/`.
- Alias `@/` trỏ tới `frontend/src/`.

## Quy tắc triển khai

1. Trước sửa, nêu mục tiêu, file dự kiến và lý do; đọc route/component/hook tương tự.
2. Dùng function component React 19 và TypeScript chặt chẽ. Props là kiểu tường minh; state cục bộ chỉ giữ dữ liệu thuộc UI. Tách logic tái sử dụng vào hook khi có lý do rõ ràng.
3. Điều hướng và bảo vệ route dùng `@tanstack/react-router` (`createFileRoute`, `Link`, `useNavigate`), không dùng router khác hoặc `window.location` trừ cơ chế xử lý phiên đã có ở `main.tsx`.
4. Dữ liệu server dùng TanStack Query: query key ổn định, queryFn gọi client generated, mutation có xử lý lỗi/thành công và invalidation đúng query key. `useSuspenseQuery` cần boundary/fallback như trang Items; query thường phải xử lý loading/error rõ ràng.
5. Form dùng React Hook Form với Zod và `@hookform/resolvers`; schema là nguồn xác thực ở UI, lỗi hiển thị cạnh field. Xác thực frontend không thay thế xác thực API.
6. Dùng `cn` từ `@/lib/utils` khi cần ghép class; giữ component nhỏ, tên phản ánh nghiệp vụ.

## Checklist

- [ ] Route đúng thư mục và không sửa `routeTree.gen.ts`.
- [ ] Props, state, hook có kiểu TypeScript; không tạo `any` tùy tiện.
- [ ] Query/mutation có key, trạng thái và invalidation hợp lý.
- [ ] Form có Zod, RHF, label và thông báo lỗi.
- [ ] Tái dùng component UI/token; không thêm dependency không được duyệt.
- [ ] Chạy `cd frontend; bun run lint` và test liên quan nếu môi trường sẵn sàng; báo rõ kết quả chạy/chưa chạy.

## Ví dụ trong repository

`frontend/src/routes/_layout/items.tsx` dùng `createFileRoute`, `useSuspenseQuery` và `ItemsService`; `frontend/src/hooks/useAuth.ts` minh họa mutation đăng nhập/đăng ký, toast, điều hướng và invalidation.
