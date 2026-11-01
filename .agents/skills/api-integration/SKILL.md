---
name: api-integration
description: Kết nối frontend với FastAPI bằng OpenAPI client đã sinh, xác minh hợp đồng API và quản lý dữ liệu bằng TanStack Query.
---

# Tích hợp API

## Khi dùng

Dùng khi frontend cần đọc/ghi API, thêm query/mutation hoặc kiểm tra hợp đồng API. Phối hợp `react-frontend`; không dùng để tự phát minh endpoint, sửa API backend hay dữ liệu database.

## Nguồn sự thật và file generated

- Cấu hình sinh client: `frontend/openapi-ts.config.ts`; đầu ra: `frontend/src/client/`.
- `frontend/src/client/client.gen.ts`, `sdk.gen.ts`, `types.gen.ts`, `core/` và `client/` là generated: không sửa trực tiếp.
- Client hiện có có thể chưa phản ánh router nghiệp vụ đang có ở `backend/app/main.py`. Đây là dấu hiệu cần xác minh, không phải lý do để đoán tên service hoặc endpoint.

## Quy trình

1. Đọc OpenAPI contract/client generated và endpoint backend liên quan chỉ để đối chiếu. Xác định phương thức, request body/query/path, response, quyền truy cập và mã lỗi từ nguồn thật.
2. Nếu contract thiếu hoặc client cũ, báo rõ khoảng cách. Chỉ chạy `cd frontend; bun run generate-client` khi backend đang phục vụ OpenAPI đúng phiên bản và việc sinh lại nằm trong task được duyệt. Sau đó review diff generated; không tự sửa từng file generated.
3. Gọi service/type từ `@/client`; client đã được cấu hình `baseURL` và auth tại `frontend/src/main.tsx`. Không tự tạo axios client khác nếu chưa có lý do.
4. Bọc call trong query/mutation TanStack Query. Dùng query key theo resource và tham số; mutation phải làm mới cache bị ảnh hưởng, hiển thị kết quả và lỗi thật từ API.
5. Không dùng mock để giả là API production. Mock chỉ dùng trong test, được cô lập và ghi rõ.

## Checklist

- [ ] Endpoint, payload, response và authorization được xác minh từ OpenAPI/client hoặc backend thật.
- [ ] Không sửa file `*.gen.ts` hay đoán service/method/type.
- [ ] Query key và invalidation phản ánh dữ liệu đã thay đổi.
- [ ] UI có loading/error/success; lỗi API không bị nuốt.
- [ ] Nếu client được generate lại, nêu nguồn OpenAPI và các file thay đổi.
- [ ] Không đưa token, secret hay nội dung `.env` vào mã, test hoặc báo cáo.

## Ví dụ trong repository

`frontend/src/hooks/useAuth.ts` import `LoginService`, `UsersService` và type từ `@/client`; `frontend/src/routes/_layout/items.tsx` gọi `ItemsService.readItems` trong query. Mẫu mới cần đi theo cách này sau khi service tương ứng được xác minh.
