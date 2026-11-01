# FixCare — Bàn giao kỹ thuật và demo

> Readiness mới nhất: [checklist demo chi tiết](hung-demo-readiness.md), gồm điều kiện thực tế, từng vai trò/route/thao tác/kết quả và ZIP bàn giao. Backend/PostgreSQL/Vite chạy được nhưng chưa có dịch vụ active, bốn tài khoản demo riêng, hồ sơ kỹ thuật và ca AVAILABLE; chưa đủ điều kiện demo ghi PostgreSQL. Hai hotfix intake scope và phân công thiếu phone đã được kiểm thử. Quyền technician xem toàn bộ danh sách khách giữ nguyên theo xác nhận của người dùng.

## Khởi động trên PowerShell

Giữ cấu hình local đang hoạt động. Không reset, seed hoặc chạy migration để chuẩn bị demo.

Từ thư mục gốc:

```powershell
docker compose up -d db mailpit
```

Terminal Backend:

```powershell
cd C:\QLDACNTTU9D\backend
uv run fastapi dev
```

Terminal Frontend:

```powershell
cd C:\QLDACNTTU9D\frontend
bun run dev
```

Không mở Backend thứ hai nếu cổng 8000 đã được FixCare dùng. Trong phiên này Backend đã được khởi động lại bằng uvicorn để nạp API mới. Vite dùng 5173; API dùng 8000.

Kiểm tra chỉ đọc:

```powershell
(Invoke-WebRequest http://127.0.0.1:8000/api/v1/openapi.json -UseBasicParsing).StatusCode
(Invoke-WebRequest http://127.0.0.1:8000/api/v1/services -UseBasicParsing).StatusCode
```

Không in response login, token hoặc nội dung .env.

## Chuẩn bị dữ liệu do người dùng nhập

Hiện API dịch vụ trả HTTP 200 nhưng **0 dịch vụ đang hoạt động**. Booking thật sẽ hiện trạng thái rỗng, không có dịch vụ giả.

Chỉ thực hiện các bước ghi dữ liệu dưới đây khi người phụ trách đồng ý dùng môi trường local/test:

1. Superuser mở `/admin`, tạo tài khoản active có role customer/staff/technician/manager cho demo. Không dùng tài khoản superuser để minh họa quyền khách hàng.
2. Quản trị/quản lý mở `/workspace/services`, thêm dịch vụ: tên, mô tả, giá tham khảo, thời lượng và active.
3. Mở `/workspace/technicians`, tạo hồ sơ kỹ thuật viên, chọn tài khoản technician từ dropdown. Danh sách chỉ gồm tài khoản active chưa liên kết; không phải tự tìm ID.
4. Chọn kỹ thuật viên, thêm ca AVAILABLE vào ngày demo. Slot dùng ca và lịch đặt thật. Hồ sơ chưa liên kết tài khoản vẫn tạo được nhưng người đó chưa thể dùng dashboard kỹ thuật.
5. Khách đăng ký/đăng nhập tài khoản riêng. Owner lấy từ token, không nhập customer_id tùy ý.

Agent **chưa thực hiện** các thao tác nhập dữ liệu này vào PostgreSQL.

## Luồng demo xuyên suốt

Dùng browser profile/cửa sổ riêng cho từng role:

| Vai trò | Route | Thao tác |
|---|---|---|
| Khách | `/`, `/services`, `/services/<id>` | Xem dịch vụ, giá tham khảo và link đặt lịch. |
| Khách | `/booking` | Chọn dịch vụ/ngày/slot, kỹ thuật viên tùy chọn; nhập thông tin máy/liên hệ; xem tóm tắt và gửi. |
| Khách | `/appointments`, `/appointments/<id>` | Xem lịch cá nhân/chi tiết/lịch sử, đổi hoặc hủy nếu trạng thái cho phép. |
| Nhân viên | `/workspace`, `/workspace/appointments`, `/workspace/queue` | Xem KPI, tìm/lọc/xác nhận lịch, phân công, tiếp nhận; đặt chỗ nhanh tại quầy. |
| Nhân viên | `/workspace/intake` | Nhập khách vãng lai, thiết bị, ngoại quan, lỗi và phụ kiện. |
| Nhân viên/kỹ thuật viên | `/workspace/repairs` | Xem phiếu được phép, cập nhật máy/chẩn đoán/ghi chú, lập báo giá nhiều hạng mục. |
| Khách | `/quotes` | Duyệt/từ chối báo giá của mình, có xác nhận. |
| Kỹ thuật viên | `/app`, `/workspace/repairs` | Chỉ xử lý phiếu được phân công, cập nhật trạng thái theo quy tắc Backend. |
| Nhân viên | `/invoices` | Báo giá ACCEPTED + phiếu COMPLETED → hóa đơn → thu tiền CASH/BANK_TRANSFER → thanh toán đủ → bàn giao. |
| Khách | `/invoices`, `/notifications`, `/reviews` | Xem hóa đơn/khoản thu riêng, đọc thông báo, đánh giá sau hoàn tất; một đánh giá/phiếu. |
| Quản lý/quản trị | `/workspace/reports` | Khoảng ngày tối đa 366 ngày, tiền thực thu, công nợ, tổng lịch, biểu đồ tháng và xuất CSV. |

Thanh toán là ghi nhận tại quầy, không chuyển tiền qua cổng thanh toán. Nút in hiện in/lưu PDF **danh sách hóa đơn**, chưa phải mẫu hóa đơn thuế/PDF riêng.

## Giải thích kiến trúc ngắn

- **Component** là khối UI dùng lại: `Operations/shared.tsx` có Panel, loading/empty/error, phân trang và ActionForm. **Props** như `fields` mô tả trường nhập, `onSubmit` chọn API; `children` là nội dung bên trong khung.
- **State** giữ lựa chọn UI như phiếu đang xem/bộ lọc. **Hook** tái dùng logic: `useQuery` đọc dữ liệu, `useMutation` ghi rồi làm mới cache sau thành công.
- **Route** là đường dẫn màn hình. Route cha render `Outlet` để trang con hiển thị; danh sách appointments ở index route, không che chi tiết nữa.
- **API** nối React với FastAPI. Generated service tạo request đúng contract OpenAPI; Axios vận chuyển HTTP và Bearer token. Không tạo HTTP client thứ hai.
- Backend kiểm tra role, owner/assignment và trạng thái trước khi SQLModel ghi PostgreSQL. Ẩn menu React không thay thế bảo vệ API.
- **Cache** là dữ liệu tạm trong trình duyệt. Đăng xuất hủy query và xóa cache để người đăng nhập sau không thấy dữ liệu cũ.
- **Idempotency** nghĩa là gửi lại không thu tiền hai lần: payment có request_id, khóa hóa đơn và kiểm tra số dư.

## Các điều kiện chưa hoàn tất

- Browser ghi nghiệp vụ xuyên suốt PostgreSQL: chưa chạy, cần database test riêng và dữ liệu được cho phép. Đã test API chain trên SQLite và UI mock có kiểm tra payload.
- SQLite không chứng minh khóa dòng/concurrency PostgreSQL. Cần kiểm thử thanh toán/đặt slot đồng thời trên database test trước production.
- Email recovery/reset: UI/API test có, gửi/nhận Mailpit thực tế chưa chạy trong phiên.
- GitHub Actions/deploy/release chưa chạy; không push/tag. Nhóm cần xác nhận bàn giao và các cuộc họp thật.
- Một số dropdown tải tối đa 100 bản ghi; danh sách chính phân trang 20. Nếu dữ liệu lớn cần tìm kiếm/phân trang phía server cho dropdown.
- Chưa audit toàn bộ accessibility, mọi viewport/trình duyệt và mọi nhánh lỗi UI.
- `role=customer` + `is_superuser=true` ở dữ liệu local chưa được sửa: Backend cho superuser vượt kiểm tra role theo thiết kế. Người quản trị cần rà soát; demo bằng các tài khoản riêng đúng role.
- Cache `.tanstack/tmp` đã bị theo dõi trong commit cũ của repository; không stage thay đổi cache trong các commit fast-track. Không tự xóa/khôi phục cache của người dùng.

## Prompt tiếp tục

> Đọc hung-fast-track-progress.md, hung-fast-track-status.md và hung-fast-track-verification.md. Không triển khai lại B–E. Ưu tiên các UID PARTIAL: E2E trên PostgreSQL test được cấp phép, email Mailpit, QA còn thiếu và CI khi có quyền. Không sửa .env, seed/reset database hoặc push nếu chưa được cho phép.

Danh sách đủ 108 UID: [status](hung-fast-track-status.md). Bằng chứng/lệnh kiểm thử: [verification](hung-fast-track-verification.md).
