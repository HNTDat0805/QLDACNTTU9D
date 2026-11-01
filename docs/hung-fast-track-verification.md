# FixCare — Bằng chứng kiểm thử fast-track

## Bổ sung demo readiness — 27/10/2026

- Chạy lại 5 module Backend có liên quan với `FIXCARE_TEST_SQLITE=1`: **58/58 PASS**, exit 0, 8,29s. Gồm test intake unassigned technician bị 403 (trước vá nhận 201), quyền catalog theo xác nhận người dùng và API chain có phân công sau tiếp nhận, chẩn đoán trước báo giá, kỹ thuật viên không có phone.
- Playwright `demo-readiness.spec.ts`, booking, appointments, operations: **22/22 PASS**, exit 0, khoảng 1 phút; `--no-deps --workers=1 --timeout=20000 --global-timeout=180000`. Spec readiness chỉ cho request GET vào API local, các spec còn lại mock API. Không chạy auth setup/không tạo phiên đăng nhập hoặc nghiệp vụ thật trong lượt readiness.
- TypeScript/build/Biome/Ruff/diff check PASS. Không đổi schema/generated client. Đã khởi động lại đúng Backend local để nạp hotfix; OpenAPI vẫn 70 path / 93 operation / 0 duplicate.
- Script `scripts/check_demo_readiness.py` kết nối PostgreSQL trong transaction READ ONLY, báo dịch vụ/4 role riêng/linked technician/ca AVAILABLE đều 0. Tài khoản role customer + superuser flag có 1; giữ nguyên.
- Chi tiết, lệnh và dữ liệu cần chuẩn bị: [readiness](hung-demo-readiness.md). Số liệu fast-track phía dưới là lịch sử, không cộng các lượt trùng nhau thành tổng testcase mới. E2E ghi PostgreSQL vẫn BLOCKED, không chuyển UID E2E sang DONE.

Ngày chạy: 27/10/2026, Windows/PowerShell. Không ghi test nghiệp vụ vào PostgreSQL. Mock chỉ tồn tại trong test; mã sản phẩm gọi generated services thật.

## Kết quả cuối và exit code

| Lượt chạy | Kết quả thực tế | Exit code |
|---|---|---:|
| Backend regression 13 modules | **152 passed**, 38,30s | 0 |
| Browser regression 9 spec + auth setup | **48 passed**, 2,2 phút | 0 |
| Bổ sung dashboard staff/technician | **2 passed**, 5,5s | 0 |
| Sau sửa cache logout: account/login/HTTP + setup | **22 passed**, 57,9s | 0 |
| TypeScript --noEmit | PASS | 0 |
| Production build cuối sau sửa cache | PASS, Vite build 2,43s | 0 |
| Biome read-only trên file thay đổi | PASS, không auto-fix cả frontend | 0 |
| Ruff check + format --check | PASS, 27 file Python | 0 |
| git diff --check | PASS | 0 |
| Runtime OpenAPI | HTTP 200; 70 path, 93 operation, 0 operationId trùng | 0 |
| Runtime public catalog | HTTP 200; 0 dịch vụ active | 0 |

48/2/22 có phần trùng nhau. Bộ spec hiện có **51 testcase khác nhau** được kiểm tra qua các lượt này; không cộng 48 + 2 + 22 thành số case độc lập. Auth setup 1, login 9, HTTP 8, account 4, booking 3, appointments 2, landing 3, layout 4, operations 16, services 1.

Không khẳng định toàn bộ suite repository đã chạy: các test template khác có thể ghi DB thật hoặc phụ thuộc Mailpit nên không chạy tùy tiện.

## Lệnh tái lập

### Backend — bắt buộc cách ly khỏi PostgreSQL

Tại `backend/`:

```powershell
$env:FIXCARE_TEST_SQLITE='1'
$env:PYTHONWARNINGS='ignore'
../.venv/Scripts/python.exe -m pytest tests/api/routes/test_login.py tests/api/routes/test_users.py tests/api/routes/test_commerce_workflow.py tests/api/routes/test_slots_and_appointments.py tests/api/routes/test_appointment_confirm_cancel.py tests/api/routes/test_appointment_history_api.py tests/api/routes/test_repair_orders_api.py tests/api/routes/test_quotes_api.py tests/api/routes/test_customers_api.py tests/api/routes/test_technicians_api.py tests/api/routes/test_work_schedules_api.py tests/api/routes/test_queue_api.py tests/api/routes/test_intake_api.py -q --tb=short
```

`FIXCARE_TEST_SQLITE=1` buộc fixture tạo engine SQLite trong bộ nhớ trước khi mở kết nối; các tài khoản/phiếu/khoản thu trong test chỉ tồn tại ở đó. Không chạy pytest không có biến này vào cấu hình PostgreSQL đang sử dụng: conftest cũ có nhánh kết nối DB cấu hình.

Bao phủ: role/owner, ẩn dữ liệu người khác, assigned technician, create/update/cancel/confirm, slot conflict, lịch làm, intake, quotes; workflow API liên hoàn đặt lịch → confirm → intake → quote → accept → IN_PROGRESS → COMPLETED → issue invoice → payment → handover → notification. Payment có kiểm tra trùng request, nội dung khác cùng key, thu dư, thu từng phần và bàn giao trước thanh toán đủ bị từ chối. Test thêm tài khoản kỹ thuật hợp lệ/không hợp lệ và response public không lộ phone/email/user_id.

SQLite không chứng minh concurrency/khóa dòng PostgreSQL; đó là kiểm thử bổ sung cần DB test riêng, không bị báo PASS ở đây.

### Frontend

Tại `frontend/`:

```powershell
bunx tsc --noEmit -p tsconfig.build.json
bun run build
```

Package hiện không có script `typecheck`; dùng tsc trực tiếp. Không dùng `bun run lint` vì script đó có `--write --unsafe` toàn repo. Lượt Biome dùng `bunx biome check <danh sách file thay đổi>` không write. Formatter chỉ từng file trong phạm vi khi cần.

Lượt regression 48:

```powershell
bunx playwright test tests/login.spec.ts tests/http-error-handling.spec.ts tests/landing.spec.ts tests/layout-routing.spec.ts tests/booking.spec.ts tests/appointments.spec.ts tests/operations.spec.ts tests/services.spec.ts tests/account-flows.spec.ts --project=chromium --workers=1 --reporter=line --timeout=25000 --global-timeout=360000
```

Sau đó thêm 2 test dashboard và 1 test cách ly phiên. Lệnh lọc dashboard đã chạy:

```powershell
bunx playwright test tests/operations.spec.ts --project=chromium --no-deps --workers=1 --reporter=line --timeout=20000 --global-timeout=90000 --grep dashboard
```

Sau hotfix cache, đã chạy lại auth thực và các test liên quan:

```powershell
bunx playwright test tests/account-flows.spec.ts tests/login.spec.ts tests/http-error-handling.spec.ts --project=chromium --workers=1 --reporter=line --timeout=25000 --global-timeout=180000
```

Chạy lại lệnh regression trên ở phiên sau sẽ thu thập 51 test hiện tại. `--no-deps` chỉ dùng với spec tự mock/storageState rỗng để không bắt chạy auth setup; không dùng để tuyên bố login thật đã PASS.

### Generator

Schema tải từ runtime đã kiểm tra bằng `/api/v1/openapi.json`; sau đó:

```powershell
bun run generate-client
```

PostProcess `scripts/normalize-generated.ts` chỉ xóa whitespace cuối dòng trong output client. Không chỉnh nghiệp vụ bằng tay trong generated files, không tắt hook Git.

## Bug log và retest

| Bug | Mức độ | Nguyên nhân/bằng chứng | Cách sửa và retest |
|---|---|---|---|
| Detail appointments chỉ hiện danh sách | Major, Sprint 3 | Route cha không render Outlet; link/direct URL không thấy form. | Parent Outlet + index list, generated route tree; test click link, reload detail, đổi/hủy PASS. |
| Generated trailing whitespace chặn commit | Minor, Sprint 1/3 | sdk.gen.ts có space cuối dòng từ generator. | PostProcess chuẩn hóa output, generate lại, diff check PASS; không chỉnh service tay. |
| Kỹ thuật viên có thể nhận dữ liệu ngoài phân công ở một số API | High, Sprint 4/5 | Review nguồn: nhánh staff role dùng chung thiếu assigned scope. | Central access helper + lọc history/queue/repair/quotes/detail/update; role/owner/assigned API tests PASS. |
| Lookup và queue update thiếu ràng buộc xác thực/quyền phù hợp | High, Sprint 3/4 | Lookup public và queue update dùng CurrentUser chung. | Lookup yêu cầu token/owner, queue RequireStaff + scope; API regression PASS. |
| Báo giá thêm dòng mất giá trị cũ | Major, Sprint 5 | key form phụ thuộc số hạng mục, remount RHF. | key theo phiếu, giữ dữ liệu khi thêm dòng; UI POST 2 items đúng số lượng/giá PASS. |
| Sidebar mobile test nhận 401 ngoài mock | Test fixture, Sprint 1 | Dashboard mới gọi appointments/me, test cũ chưa chặn request này. | Bổ sung mock endpoint rỗng trong layout test, giữ assertion sidebar/theme; regression PASS. |
| Tiêu đề Panel chưa là heading; main lồng nhau | Accessibility, Sprint 5–7 | Snapshot review có text 5/5 sao nhưng không có heading; nested main. | Panel dùng h2, layout chỉ một main; review test giữ semantic assertion PASS; nối lỗi field bằng aria-describedby. |
| Cache báo giá A hiển thị tạm khi đăng nhập B | High, Sprint 2/7 | Test đổi tài khoản FAIL: QUO-PRIVATE-A vẫn visible khi API B đang chờ. | Logout hủy queries + clear cache; test tương tự PASS; auth/login/HTTP regression 22/22 PASS. |
| Test mới dùng sai field/tên nút | Test code, không phải app bug | reported_fault thay cho fault_description; tên nút gửi quote sai. | Sửa theo schema/UI thật, giữ kiểm tra payload/thành công, retest PASS. |

Các assertion bảo mật, đổi/hủy, điều hướng và số tiền không bị bỏ/xóa để đạt PASS. Những test Backend cũ được cập nhật để xác thực đúng owner hoặc linked technician sau khi vá quyền; vẫn giữ assertions conflict/rollback/state.

## Phần chưa được chứng minh

- E2E browser nghiệp vụ ghi PostgreSQL: **NOT RUN**, cần DB test riêng và dữ liệu được phép.
- Runtime public technician choices với một dịch vụ thật: chưa kiểm tra trên PostgreSQL do catalog đang rỗng; đã test API trên SQLite với dữ liệu fixture và UI mock.
- SMTP/Mailpit gửi/nhận reset email thực: **NOT RUN**; UI + API reset có test riêng.
- CI GitHub, deployment, performance/load, toàn bộ mypy backend, Firefox/WebKit, PDF in thực: **NOT RUN**.
- Đối chiếu đầy đủ wireframe/acceptance từng Sprint, UAT và 7 cuộc họp/release: chưa có xác nhận người phụ trách.
- Role customer + is_superuser=true trong local: giữ nguyên, không tự đổi quyền/dữ liệu.
- Kiểm tra bí mật áp dụng lên file/diff staged; không chạy scanner dịch vụ ngoài. Không stage .env, auth state, cache hoặc token thực.

## Phân biệt kết quả

**PASS**: lệnh đã kết thúc exit 0/assertion đạt. **FAIL**: lỗi từng xảy ra, đã ghi bug/retest; không che bằng tăng timeout. **NOT RUN**: chưa chạy nên không coi hoàn thành. **BLOCKED**: cần môi trường/dữ liệu/quyền hoặc bằng chứng từ người thật.

Bảng [108 UID](hung-fast-track-status.md) tách task viết màn hình đã test khỏi task E2E/DoD/họp/release. Hướng dẫn demo và giải thích code theo nhóm: [demo](hung-fast-track-demo.md).
