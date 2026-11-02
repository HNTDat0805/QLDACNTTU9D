# FixPhone – Hệ Thống Đặt Lịch Và Quản Lý Sửa Chữa Điện Thoại

Tài liệu hướng dẫn kỹ thuật, thiết lập môi trường và vận hành **Backend FastAPI** cho dự án **FixPhone**.

---

## Mục lục

1. [Giới thiệu dự án FixPhone](#1-giới-thiệu-dự-án-fixphone)
2. [Công nghệ Backend thực tế sử dụng](#2-công-nghệ-backend-thực-tế-sử-dụng)
3. [Cấu trúc thư mục Backend](#3-cấu-trúc-thư-mục-backend)
4. [Điều kiện môi trường cần thiết](#4-điều-kiện-môi-trường-cần-thiết)
5. [Hướng dẫn clone repository](#5-hướng-dẫn-clone-repository)
6. [Hướng dẫn tạo và kích hoạt virtual environment](#6-hướng-dẫn-tạo-và-kích-hoạt-virtual-environment)
7. [Hướng dẫn cài đặt dependencies](#7-hướng-dẫn-cài-đặt-dependencies)
8. [Hướng dẫn cấu hình biến môi trường](#8-hướng-dẫn-cấu-hình-biến-môi-trường)
9. [Hướng dẫn kết nối PostgreSQL](#9-hướng-dẫn-kết-nối-postgresql)
10. [Hướng dẫn chạy migration và nạp dữ liệu ban đầu](#10-hướng-dẫn-chạy-migration-và-nạp-dữ-liệu-ban-đầu)
11. [Hướng dẫn khởi chạy FastAPI](#11-hướng-dẫn-khởi-chạy-fastapi)
12. [Địa chỉ Swagger UI và OpenAPI JSON](#12-địa-chỉ-swagger-ui-và-openapi-json)
13. [Hướng dẫn kiểm tra Backend hoạt động](#13-hướng-dẫn-kiểm-tra-backend-hoạt-động)
14. [Các lỗi thường gặp và cách xử lý (Troubleshooting)](#14-các-lỗi-thường-gặp-và-cách-xử-lý-troubleshooting)

---

## 1. Giới thiệu dự án FixPhone

**FixPhone** là hệ thống phần mềm quản lý toàn diện quy trình tiếp nhận, đặt lịch và sửa chữa thiết bị di động, được xây dựng theo kiến trúc hướng dịch vụ với hiệu năng cao, bảo mật chặt chẽ và khả năng mở rộng linh hoạt.

### Các phân hệ và tính năng cốt lõi:
- **Khách hàng (Customer)**:
  - Tra cứu danh mục dịch vụ sửa chữa và bảng giá công khai.
  - Đặt lịch hẹn sửa chữa trực tuyến theo từng khung giờ (Time Slots) linh hoạt, hỗ trợ cơ chế khóa tranh chấp (concurrency lock) tránh trùng lịch.
  - Quản lý danh sách thiết bị của khách hàng (IMEI, dòng máy, tình trạng).
  - Theo dõi tiến độ đơn hàng sửa chữa thời gian thực.
  - Xem báo giá chi tiết, hóa đơn thanh toán và gửi đánh giá dịch vụ (Reviews).
- **Kỹ thuật viên (Technician)**:
  - Quản lý lịch làm việc hàng tuần (Work Schedules).
  - Tiếp nhận đơn sửa chữa (Repair Orders) được phân công.
  - Cập nhật chẩn đoán lỗi, linh kiện thay thế và trạng thái sửa chữa.
- **Quản trị viên & Nhân viên (Admin / Manager / Staff)**:
  - Tiếp nhận máy tại quầy (Intake Record) và xếp hàng phục vụ (Queue).
  - Lập báo giá phụ tùng, linh kiện và tiền công (Quotes).
  - Quản lý xuất hóa đơn (Invoices), tính toán thuế/chiết khấu và ghi nhận thanh toán (Payments) với cơ chế bảo vệ ngăn chặn trùng lặp giao dịch (Idempotency).
  - Quản trị tài khoản người dùng, phân quyền theo vai trò (RBAC) và quản lý hệ thống thông báo (Notifications).

---

## 2. Công nghệ Backend thực tế sử dụng

Backend của FixPhone được xây dựng trên nền tảng Python hiện đại với các công nghệ và thư viện chính thức sau (căn cứ theo `backend/pyproject.toml`):

| Thành phần | Công nghệ / Thư viện | Phiên bản | Mô tả vai trò |
| :--- | :--- | :--- | :--- |
| **Ngôn ngữ** | Python | `>= 3.14, < 4.0` | Ngôn ngữ lập trình chính của Backend |
| **Framework** | [FastAPI](https://fastapi.tiangolo.com) | `>= 0.141.1` | Web framework bất đồng bộ (ASGI) hiệu năng cao, tự động sinh OpenAPI spec |
| **ORM & Data Model** | [SQLModel](https://sqlmodel.tiangolo.com) | `>= 0.0.39` | Kết hợp SQLAlchemy 2.0 và Pydantic v2 cho truy vấn cơ sở dữ liệu và xác thực schema |
| **Database Driver** | [psycopg](https://www.psycopg.org/psycopg3/) (v3) | `>= 3.3.4` | Driver kết nối PostgreSQL hiệu năng cao, hỗ trợ chuẩn connection pool `pool_pre_ping` |
| **Database Migration** | [Alembic](https://alembic.sqlalchemy.org) | `>= 1.19.1` | Quản lý và thực thi các phiên bản thay đổi schema cơ sở dữ liệu |
| **Cơ sở dữ liệu** | [PostgreSQL](https://www.postgresql.org) | `18` (hoặc `15+`) | Hệ quản trị cơ sở dữ liệu quan hệ chính |
| **Package Manager** | [uv](https://docs.astral.sh/uv/) | Bản mới nhất | Trình quản lý package và virtual environment cực nhanh bằng Rust |
| **Bảo mật & Token** | [PyJWT](https://pyjwt.readthedocs.io) | `>= 2.13.0` | Tạo và xác thực chuẩn JWT Access Token và Refresh Token rotation |
| **Băm mật khẩu** | [pwdlib](https://github.com/frankie567/pwdlib) | `>= 0.3.1` | Hỗ trợ thuật toán băm an toàn hiện đại Argon2id và Bcrypt |
| **Xác thực dữ liệu** | [Pydantic](https://docs.pydantic.dev) | `> 2.0` | Data validation, Settings management (`pydantic-settings >= 2.2.1`) |
| **Hệ thống Email** | `emails`, `jinja2` | Jinja2 `>= 3.1.4` | Tạo và gửi email giao dịch (kèm React Email templates) |
| **Logging & Giám sát** | `sentry-sdk`, Custom Logging | Sentry `>= 2.68.1` | Structured logging (Text/JSON) kèm Middleware gắn `X-Request-ID` tracing |
| **Kiểm thử tự động** | [Pytest](https://pytest.org) | `>= 7.4.3` | Khung kiểm thử tự động toàn diện với coverage report |
| **Code Quality** | [Ruff](https://docs.astral.sh/ruff/), [Mypy](https://mypy.readthedocs.io) | Ruff `>= 0.2.2`, Mypy `>= 1.8.0` | Linter, code formatter và static type checking (strict mode) |

---

## 3. Cấu trúc thư mục Backend

```text
backend/
├── app/
│   ├── alembic/                  # Quản lý migration cơ sở dữ liệu
│   │   ├── versions/             # Danh sách file migration version (.py)
│   │   └── env.py                # Cấu hình môi trường kết nối Alembic với SQLModel
│   ├── api/                      # Định tuyến và các API endpoints
│   │   ├── routes/               # Xử lý logic từng phân hệ nghiệp vụ:
│   │   │   ├── appointments.py   # Quản lý đặt lịch hẹn & booking
│   │   │   ├── customers.py      # Hồ sơ khách hàng
│   │   │   ├── devices.py        # Quản lý thiết bị của khách
│   │   │   ├── intake.py         # Tiếp nhận máy tại quầy & biên bản bàn giao
│   │   │   ├── invoices.py       # Quản lý hóa đơn sửa chữa & chi phí
│   │   │   ├── items.py          # CRUD items mẫu từ template
│   │   │   ├── login.py          # Đăng nhập, refresh token, cấp phát JWT
│   │   │   ├── notifications.py  # Hệ thống thông báo người dùng
│   │   │   ├── payments.py       # Ghi nhận thanh toán & chống thanh toán lặp
│   │   │   ├── queue.py          # Quản lý hàng đợi tiếp nhận
│   │   │   ├── quotes.py         # Báo giá sửa chữa (tiền công + linh kiện)
│   │   │   ├── repair_orders.py  # Đơn hàng sửa chữa & cập nhật tiến độ
│   │   │   ├── reviews.py        # Đánh giá và nhận xét dịch vụ
│   │   │   ├── services.py       # Danh mục và bảng giá dịch vụ sửa chữa
│   │   │   ├── slots.py          # Khung giờ làm việc & kiểm tra slot trống
│   │   │   ├── technicians.py    # Thông tin & hồ sơ kỹ thuật viên
│   │   │   ├── users.py          # Quản trị người dùng và phân quyền (RBAC)
│   │   │   ├── utils.py          # Endpoints tiện ích (health check, test email)
│   │   │   └── work_schedules.py # Lịch làm việc theo tuần của kỹ thuật viên
│   │   ├── deps.py               # Dependency Injection (DB Session, Current User, Role Check)
│   │   └── main.py               # Gom nhóm toàn bộ sub-routers vào API router chính
│   ├── core/                     # Cấu hình hệ thống và hạ tầng Backend
│   │   ├── config.py             # Quản lý cấu hình & biến môi trường bằng Pydantic BaseSettings
│   │   ├── db.py                 # Khởi tạo SQLAlchemy Engine, cấu hình connection pool
│   │   ├── db_restore.py         # Tiện ích khôi phục (restore) cơ sở dữ liệu từ file backup
│   │   ├── logging.py            # Cấu hình logging chuẩn hóa (Text/JSON format)
│   │   ├── middleware.py         # Middleware ghi log request và đính kèm X-Request-ID
│   │   └── security.py           # Mã hóa mật khẩu (Argon2/Bcrypt) và xử lý JWT Token
│   ├── email-templates/          # Mẫu HTML email giao dịch
│   ├── crud.py                   # Thao tác truy vấn cơ sở dữ liệu cơ bản (CRUD)
│   ├── initial_data.py           # Script nạp tài khoản Superuser ban đầu vào DB
│   ├── main.py                   # Điểm khởi chạy chính của ứng dụng FastAPI
│   ├── models.py                 # Định nghĩa toàn bộ SQLModel tables & Pydantic schemas
│   └── utils.py                  # Hàm tiện ích gửi email, token đặt lại mật khẩu
├── scripts/                      # Shell scripts hỗ trợ kiểm thử và tự động hóa
│   ├── prestart.sh               # Thực thi migration và nạp initial data
│   ├── test.sh                   # Chạy bộ kiểm thử pytest và xuất coverage
│   ├── lint.sh                   # Kiểm tra code style với ruff và mypy
│   └── format.sh                 # Format code tự động với ruff
├── tests/                        # Bộ kiểm thử tự động (Unit / Integration Tests)
│   ├── api/                      # Kiểm thử chi tiết các API endpoints
│   ├── core/                     # Kiểm thử bảo mật, token, hash mật khẩu, restore DB
│   ├── crud/                     # Kiểm thử các thao tác CRUD
│   └── conftest.py               # Fixtures cấu hình database test và HTTP TestClient
├── alembic.ini                   # Cấu hình công cụ Alembic
└── pyproject.toml                # Cấu hình dự án, dependencies và các tool (uv, ruff, mypy, pytest)
```

---

## 4. Điều kiện môi trường cần thiết

Trước khi cài đặt và chạy Backend, hãy đảm bảo hệ thống đáp ứng các yêu cầu sau:

1. **Hệ điều hành**: Windows 10/11, macOS, hoặc Linux (Ubuntu 20.04+).
2. **Python**: Phiên bản `>= 3.14, < 4.0` (theo khai báo `requires-python` trong `pyproject.toml`).
3. **Trình quản lý package `uv`**:
   - Cài đặt trên Windows (PowerShell):
     ```powershell
     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```
   - Cài đặt trên macOS / Linux:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
4. **Cơ sở dữ liệu PostgreSQL**:
   - Khuyến nghị: Cài đặt **Docker** & **Docker Compose** để chạy container PostgreSQL 18 và Mailpit có sẵn cấu hình.
   - Hoặc: Cài đặt PostgreSQL 15+ cục bộ trên máy host (cần có công cụ client `psql`).
5. **Git**: Phiên bản mới nhất để clone source code.

---

## 5. Hướng dẫn clone repository

Mở terminal hoặc PowerShell và thực hiện:

```bash
# Clone source code dự án từ GitHub
git clone https://github.com/HNTDat0805/QLDACNTTU9D.git

# Di chuyển vào thư mục gốc của dự án
cd QLDACNTTU9D
```

---

## 6. Hướng dẫn tạo và kích hoạt virtual environment

Dự án khuyến khích sử dụng `uv` để tạo môi trường ảo nhanh chóng và chuẩn xác:

### Bước 1: Tạo môi trường ảo
Tại thư mục gốc dự án (hoặc trong thư mục `backend/`):
```bash
uv venv
```
Môi trường ảo sẽ được khởi tạo trong thư mục `.venv/`.

### Bước 2: Kích hoạt môi trường ảo
- **Trên Windows (PowerShell)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
  *(Nếu gặp lỗi Execution Policy, chạy `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*
- **Trên Windows (Command Prompt - CMD)**:
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **Trên Linux / macOS (Bash/Zsh)**:
  ```bash
  source .venv/bin/activate
  ```

> **Mẹo**: Khi sử dụng cú pháp `uv run <lệnh>`, `uv` sẽ tự động kích hoạt môi trường ảo mà bạn không cần phải chạy lệnh activate thủ công.

---

## 7. Hướng dẫn cài đặt dependencies

Để cài đặt đầy đủ các thư viện Backend (bao gồm cả các thư viện kiểm thử và kiểm tra mã nguồn):

```bash
# Di chuyển vào thư mục backend
cd backend

# Cài đặt toàn bộ dependencies theo lockfile
uv sync
```

Lệnh `uv sync` sẽ cài đặt các gói chính (`fastapi`, `sqlmodel`, `alembic`, `psycopg`, `pydantic`, `pyjwt`, `pwdlib`...) và các nhóm phụ thuộc phát triển (`pytest`, `mypy`, `ruff`, `coverage`).

---

## 8. Hướng dẫn cấu hình biến môi trường

Backend đọc biến môi trường từ file `.env` đặt tại thư mục gốc của dự án (`QLDACNTTU9D/.env`).

### Bước 1: Tạo file `.env` từ file mẫu
- **Trên Windows PowerShell**:
  ```powershell
  Copy-Item .env.example .env
  ```
- **Trên Linux / macOS / Git Bash**:
  ```bash
  cp .env.example .env
  ```

### Bước 2: Thiết lập các biến môi trường chi tiết
Mở file `.env` và điều chỉnh các giá trị phù hợp với môi trường của bạn:

```env
# Chế độ phát triển (bật tính năng docs, test routes và cảnh báo secret mặc định)
FASTAPI_ENV=development

# Tên dự án hiển thị trên tiêu đề Swagger UI và thông tin OpenAPI
PROJECT_NAME="FixPhone - He Thong Dat Lich Va Sua Chua Dien Thoai"

# Khóa bí mật dùng để ký JWT token (tối thiểu 32 ký tự, bắt buộc đổi khi triển khai thật)
SECRET_KEY=changethis

# Tài khoản quản trị cấp cao nhất (Superuser) khởi tạo mặc định
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=changethis

# Cấu hình dịch vụ gửi email (mặc định trỏ về Mailpit để test cục bộ)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_TLS=False
EMAILS_FROM_EMAIL=info@fixphone.local

# Cấu hình kết nối cơ sở dữ liệu PostgreSQL
POSTGRES_PASSWORD=changethis
DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@localhost:5432/app

# Cấu hình Logging (DEBUG, INFO, WARNING, ERROR, CRITICAL | format: text hoặc json)
LOG_LEVEL=INFO
LOG_FORMAT=text
LOG_SQL_QUERIES=False
```

> **Cảnh báo bảo mật**:
> - Tuyệt đối không commit file `.env` chứa mật khẩu thật lên GitHub.
> - Trong môi trường Production (`FASTAPI_ENV` khác `development`), hệ thống sẽ ném ngoại lệ và dừng khởi động nếu `SECRET_KEY`, `POSTGRES_PASSWORD` hoặc `FIRST_SUPERUSER_PASSWORD` còn để giá trị mặc định `"changethis"`.
> - Bạn có thể sinh chuỗi secret ngẫu nhiên an toàn bằng lệnh:
>   ```bash
>   python -c "import secrets; print(secrets.token_urlsafe(32))"
>   ```

---

## 9. Hướng dẫn kết nối PostgreSQL

### Phương án A: Khởi chạy PostgreSQL bằng Docker Compose (Khuyến nghị)
Hệ thống đã chuẩn bị sẵn service PostgreSQL 18 và Mailpit trong file `compose.yml`. Từ thư mục gốc dự án, thực hiện:

```bash
docker compose up -d db mailpit
```

- PostgreSQL container sẽ khởi động tại cổng `5432`, tự tạo database `app` và user `postgres`.
- Mailpit khởi động tại cổng `8025` (Web UI xem email) và `1025` (nhận email SMTP).
- Kiểm tra trạng thái dịch vụ:
  ```bash
  docker compose ps
  ```

### Phương án B: Sử dụng PostgreSQL cài đặt trực tiếp trên máy
Nếu sử dụng PostgreSQL độc lập có sẵn trên máy:
1. Đảm bảo dịch vụ PostgreSQL đang chạy:
   ```bash
   pg_isready -h localhost -p 5432 -U postgres
   ```
2. Mở PostgreSQL CLI và tạo database tên là `app`:
   ```sql
   CREATE DATABASE app;
   ```
3. Cập nhật biến `POSTGRES_PASSWORD` và `DATABASE_URL` trong file `.env` cho đúng với mật khẩu của PostgreSQL trên máy bạn.

---

## 10. Hướng dẫn chạy migration và nạp dữ liệu ban đầu

Dự án FixPhone quản lý cơ sở dữ liệu thông qua **Alembic**.

### Bước 1: Thực thi migration nâng cấp cơ sở dữ liệu
Tại thư mục `backend/`, chạy lệnh:
```bash
cd backend
uv run alembic upgrade head
```
Lệnh trên sẽ quét toàn bộ các phiên bản trong thư mục `app/alembic/versions/` và tạo đầy đủ các bảng dữ liệu: `user`, `customer`, `technician`, `service`, `timeslot`, `appointment`, `workschedule`, `queueentry`, `deviceintake`, `quote`, `customerdevice`, `repairorder`, `invoice`, `payment`, `review`, `notification`.

### Bước 2: Nạp dữ liệu tài khoản quản trị ban đầu
Tạo tài khoản Superuser đầu tiên căn cứ theo giá trị `FIRST_SUPERUSER` và `FIRST_SUPERUSER_PASSWORD` trong file `.env`:
- **Trên Windows PowerShell / CMD**:
  ```powershell
  uv run python app/initial_data.py
  ```
- **Trên Linux / macOS / Git Bash**:
  ```bash
  uv run bash scripts/prestart.sh
  ```
Khi hoàn tất, terminal sẽ thông báo: `Initial data created`.

### Bước 3: Tạo migration mới (khi thay đổi SQLModel)
Nếu bạn thay đổi hoặc bổ sung trường dữ liệu trong `app/models.py`:
```bash
uv run alembic revision --autogenerate -m "Ten mo ta thay doi"
uv run alembic upgrade head
```

---

## 11. Hướng dẫn khởi chạy FastAPI

Từ thư mục `backend/`, bạn có thể khởi chạy server theo một trong hai cách:

### Cách 1: Sử dụng FastAPI CLI (Khuyến nghị cho lập trình viên)
```bash
uv run fastapi dev
```
*(FastAPI CLI tự động nạp cấu hình entrypoint `app.main:app`, tự reload khi sửa code, và lắng nghe tại cổng `8000`).*

### Cách 2: Sử dụng Uvicorn trực tiếp
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Kết quả hiển thị thành công:
```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

---

## 12. Địa chỉ Swagger UI và OpenAPI JSON

Khi server Backend đang chạy, toàn bộ tài liệu API được cung cấp trực tiếp tại các địa chỉ:

| Giao diện / Tài liệu | URL truy cập | Mục đích sử dụng |
| :--- | :--- | :--- |
| **Swagger UI** | [http://localhost:8000/docs](http://localhost:8000/docs) | Giao diện tương tác trực quan: xem chi tiết endpoint, schema request/response, thử nghiệm gọi API (`Try it out`), đăng nhập Bearer Token |
| **ReDoc** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Giao diện tài liệu kỹ thuật chuẩn, trình bày cấu trúc dữ liệu rõ ràng |
| **OpenAPI Schema (JSON)** | [http://localhost:8000/api/v1/openapi.json](http://localhost:8000/api/v1/openapi.json) | File JSON định dạng chuẩn OpenAPI 3.1.0, dùng để import vào Postman, Insomnia hoặc sinh client frontend tự động |

### Các nhóm API chính trên Swagger:
- **`login`**: Đăng nhập lấy access token & refresh token (`/api/v1/login/access-token`), refresh token xoay vòng (`/api/v1/login/refresh`), khôi phục mật khẩu qua email.
- **`users`**: Quản lý thông tin tài khoản, phân quyền Role (Admin, Manager, Staff, Technician, Customer), đổi mật khẩu.
- **`services`**: Danh mục dịch vụ sửa chữa (thay màn hình, thay pin, ép kính, sửa nguồn...), đơn giá và thời gian dự kiến.
- **`slots`**: Quản lý khung giờ làm việc theo ngày và kiểm tra slot còn trống.
- **`appointments` / `bookings`**: Đặt lịch hẹn sửa chữa trực tuyến của khách hàng, khóa giao dịch tranh chấp slot.
- **`customers` & `technicians`**: Quản lý thông tin chi tiết hồ sơ khách hàng và kỹ thuật viên.
- **`devices` & `intake`**: Tiếp nhận thiết bị tại quầy, kiểm tra ngoại quan máy và in phiếu tiếp nhận.
- **`quotes`**: Lập báo giá chi tiết gồm tiền linh kiện và chi phí công thợ.
- **`repair_orders`**: Quản lý vòng đời đơn sửa chữa (đang kiểm tra, chờ linh kiện, đang sửa, hoàn thành, hủy đơn).
- **`invoices` & `payments`**: Xuất hóa đơn sửa chữa, tính toán thuế/chiết khấu, ghi nhận thanh toán đa phương thức và chống trùng lặp giao dịch thanh toán.
- **`reviews`**: Tiếp nhận đánh giá số sao và phản hồi chất lượng từ khách hàng.
- **`notifications`**: Hệ thống thông báo trong app cho người dùng.
- **`utils`**: Health check kiểm tra trạng thái hoạt động của hệ thống và gửi email thử nghiệm.

> **Lưu ý về tiền tố URL**: Toàn bộ endpoints hỗ trợ cả hai tiền tố: `/api/v1/...` (chuẩn RESTful) và `/api/...` (bí danh trực tiếp).

---

## 13. Hướng dẫn kiểm tra Backend hoạt động

### 1. Kiểm tra Health Check Endpoint
Gửi yêu cầu HTTP GET đến endpoint sức khỏe của hệ thống:
```bash
curl -i http://localhost:8000/api/v1/utils/health-check/
```
- **Mã phản hồi mong đợi**: `HTTP/1.1 200 OK`
- **Dữ liệu trả về**: `true`

### 2. Chạy bộ kiểm thử tự động toàn diện (Pytest)
Dự án được tích hợp bộ test tự động kiểm thử toàn bộ các ca nghiệp vụ nhạy cảm (bảo mật xác thực, phân quyền RBAC, kiểm tra dữ liệu đầu vào, đặt trùng slot đồng thời, tính tiền và ngăn thanh toán lặp, restore cơ sở dữ liệu):

```bash
cd backend

# Chạy toàn bộ test suite
uv run pytest

# Hoặc chạy kiểm thử kèm báo cáo độ phủ chi tiết
uv run pytest --cov=app tests/
```

Toàn bộ các ca kiểm thử trong thư mục `tests/` phải đạt kết quả **PASSED** (100%).

---

## 14. Các lỗi thường gặp và cách xử lý (Troubleshooting)

### 1. Lỗi xung đột cổng `8000` (`Address already in use` / `Port 8000 is already in use`)
- **Nguyên nhân**: Một tiến trình FastAPI hoặc ứng dụng khác đang chiếm giữ cổng `8000`.
- **Cách xử lý**:
  - Trên Windows (PowerShell):
    ```powershell
    netstat -ano | findstr :8000
    # Tìm mã PID ở cột cuối cùng và tắt tiến trình:
    taskkill /F /PID <MÃ_PID>
    ```
  - Hoặc khởi chạy FastAPI trên cổng khác:
    ```bash
    uv run uvicorn app.main:app --reload --port 8001
    ```

### 2. Lỗi kết nối PostgreSQL (`ConnectionRefusedError` / `could not connect to server`)
- **Nguyên nhân**: Dịch vụ PostgreSQL chưa được bật, hoặc chuỗi kết nối trong file `.env` bị sai thông tin đăng nhập.
- **Cách xử lý**:
  - Nếu dùng Docker, hãy khởi động lại container:
    ```bash
    docker compose up -d db
    docker compose ps
    ```
  - Đảm bảo mật khẩu trong biến `POSTGRES_PASSWORD` và trong `DATABASE_URL` hoàn toàn đồng nhất.
  - Chờ khoảng 5-10 giây để container PostgreSQL hoàn tất quá trình khởi tạo dữ liệu ban đầu.

### 3. Lỗi `alembic.util.exc.CommandError: Target database is not up to date`
- **Nguyên nhân**: Cơ sở dữ liệu chưa được đồng bộ cấu trúc bảng lên phiên bản migration mới nhất.
- **Cách xử lý**:
  ```bash
  cd backend
  uv run alembic upgrade head
  ```

### 4. Lỗi `401 Unauthorized` khi gọi các API yêu cầu đăng nhập
- **Nguyên nhân**: Chưa đính kèm JWT token vào HTTP Header hoặc token đã hết hạn.
- **Cách xử lý**:
  - Gửi request đến `POST /api/v1/login/access-token` với form data `username` và `password` để lấy token mới.
  - Thêm header vào request: `Authorization: Bearer <access_token>`.
  - Trên giao diện Swagger UI, nhấp vào nút **Authorize** (biểu tượng ổ khóa màu xanh ở góc trên bên phải) và dán token vào.

### 5. Cảnh báo an toàn `The value of SECRET_KEY is "changethis"`
- **Nguyên nhân**: Hệ thống đang chạy với chuỗi bí mật mặc định của template.
- **Cách xử lý**:
  - Mở file `.env` và đổi `SECRET_KEY`, `FIRST_SUPERUSER_PASSWORD`, `POSTGRES_PASSWORD` thành các giá trị an toàn ngẫu nhiên.
