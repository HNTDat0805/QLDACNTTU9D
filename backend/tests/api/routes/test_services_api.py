import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Service
from app.services import service_catalog_service


def create_sample_service(
    db: Session,
    code: str | None = None,
    name: str | None = None,
    description: str | None = "Mô tả dịch vụ mẫu cho kiểm thử",
    base_price: float = 350_000.0,
    estimated_duration_minutes: int = 30,
    is_active: bool = True,
) -> Service:
    """Hàm tiện ích tạo nhanh bản ghi Service trong database phục vụ kiểm thử."""
    suffix = uuid.uuid4().hex[:6].upper()
    svc_code = code or f"SVC-UNIT-{suffix}"
    svc_name = name or f"Dịch Vụ Kiểm Thử {suffix}"

    svc = Service(
        id=uuid.uuid4(),
        code=svc_code,
        name=svc_name,
        description=description,
        base_price=base_price,
        estimated_duration_minutes=estimated_duration_minutes,
        is_active=is_active,
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)
    return svc


# ============================================================================
# TEST SUITE: KIỂM THỬ ĐƠN VỊ API DỊCH VỤ (TASK: HỒ NGUYỄN TẤN ĐẠT)
# ============================================================================


def test_tc01_get_services_list_success(client: TestClient, db: Session) -> None:
    """
    [TC01] Lấy danh sách dịch vụ thành công.
    - Mục tiêu: Khách hàng / Public có thể truy cập danh mục dịch vụ mà không cần đăng nhập.
    - Kết quả mong đợi: HTTP 200 OK, trả về danh sách dịch vụ dạng JSON.
    - Kiểm tra cả 2 route alias: /api/services và /api/v1/services.
    """
    svc = create_sample_service(db, is_active=True)

    # 1. Kiểm tra endpoint /api/services
    res1 = client.get("/api/services")
    assert res1.status_code == 200
    data1 = res1.json()
    assert "data" in data1
    assert "count" in data1
    assert data1["count"] >= 1
    returned_ids1 = [item["id"] for item in data1["data"]]
    assert str(svc.id) in returned_ids1

    # 2. Kiểm tra route alias /api/v1/services
    res2 = client.get("/api/v1/services")
    assert res2.status_code == 200
    data2 = res2.json()
    returned_ids2 = [item["id"] for item in data2["data"]]
    assert str(svc.id) in returned_ids2


def test_tc02_get_services_response_schema(client: TestClient, db: Session) -> None:
    """
    [TC02] Danh sách dịch vụ trả về đúng cấu trúc dữ liệu (Schema Validation).
    - Mục tiêu: Đảm bảo payload trả về tuân thủ cấu trúc Pydantic schema ServicesPublic và ServicePublic.
    - Kết quả mong đợi:
      + Cấp cao nhất gồm 'data' (list) và 'count' (int >= 0).
      + Mỗi phần tử trong 'data' chứa đầy đủ các trường:
        id, code, name, description, base_price, estimated_duration_minutes, is_active, created_at, updated_at.
    """
    svc = create_sample_service(
        db,
        description="Chi tiết kiểm tra schema",
        base_price=450_000.0,
        estimated_duration_minutes=45,
        is_active=True,
    )

    response = client.get(f"/api/services?q={svc.code}")
    assert response.status_code == 200
    payload = response.json()

    assert isinstance(payload, dict)
    assert isinstance(payload["data"], list)
    assert isinstance(payload["count"], int)
    assert payload["count"] >= 1

    item = next(x for x in payload["data"] if x["id"] == str(svc.id))
    # Kiểm tra kiểu dữ liệu từng trường
    assert item["id"] == str(svc.id)
    assert item["code"] == svc.code
    assert item["name"] == svc.name
    assert item["description"] == "Chi tiết kiểm tra schema"
    assert isinstance(item["base_price"], float | int)
    assert item["base_price"] == 450_000.0
    assert isinstance(item["estimated_duration_minutes"], int)
    assert item["estimated_duration_minutes"] == 45
    assert isinstance(item["is_active"], bool)
    assert item["is_active"] is True
    assert "created_at" in item
    assert "updated_at" in item


def test_tc03_get_service_by_id_success(client: TestClient, db: Session) -> None:
    """
    [TC03] Lấy chi tiết một dịch vụ tồn tại.
    - Mục tiêu: Truy vấn chi tiết một dịch vụ thông qua ID hợp lệ.
    - Kết quả mong đợi: HTTP 200 OK, trả về thông tin chi tiết chính xác của dịch vụ.
    """
    svc = create_sample_service(
        db,
        code="SVC-DETAIL-TEST",
        name="Thay Pin iPhone Chính Hãng",
        description="Pin bảo hành 12 tháng, đổi mới nếu lỗi.",
        base_price=650_000.0,
        estimated_duration_minutes=25,
        is_active=True,
    )

    # 1. Gọi /api/services/{id}
    response = client.get(f"/api/services/{svc.id}")
    assert response.status_code == 200
    detail = response.json()

    assert detail["id"] == str(svc.id)
    assert detail["code"] == "SVC-DETAIL-TEST"
    assert detail["name"] == "Thay Pin iPhone Chính Hãng"
    assert detail["description"] == "Pin bảo hành 12 tháng, đổi mới nếu lỗi."
    assert detail["base_price"] == 650_000.0
    assert detail["estimated_duration_minutes"] == 25
    assert detail["is_active"] is True

    # 2. Gọi alias /api/v1/services/{id}
    res_v1 = client.get(f"/api/v1/services/{svc.id}")
    assert res_v1.status_code == 200
    assert res_v1.json()["id"] == str(svc.id)


def test_tc04_get_service_by_id_not_found(client: TestClient) -> None:
    """
    [TC04] Truy vấn dịch vụ không tồn tại.
    - Mục tiêu: Kiểm tra xử lý lỗi khi client truyền UUID hợp lệ nhưng không có trong database.
    - Kết quả mong đợi: HTTP 404 Not Found, thông báo lỗi 'Không tìm thấy dịch vụ với ID...'.
    """
    non_existent_id = uuid.uuid4()
    response = client.get(f"/api/services/{non_existent_id}")

    assert response.status_code == 404
    error_body = response.json()
    assert "detail" in error_body
    assert f"Không tìm thấy dịch vụ với ID {non_existent_id}" in error_body["detail"]


def test_tc05_get_service_by_id_invalid_uuid(client: TestClient) -> None:
    """
    [TC05] Kiểm tra dữ liệu đầu vào không hợp lệ cho tham số path service_id.
    - Mục tiêu: Kiểm tra xác thực kiểu dữ liệu UUID tại path parameter.
    - Dữ liệu kiểm thử: '12345', 'not-a-uuid', 'abc@xyz'.
    - Kết quả mong đợi: HTTP 422 Unprocessable Entity, FastApi/Pydantic validation error.
    """
    for invalid_id in ["12345", "not-a-uuid", "abc@xyz", "---"]:
        response = client.get(f"/api/services/{invalid_id}")
        assert response.status_code == 422
        body = response.json()
        assert "detail" in body
        assert any(err.get("loc") == ["path", "service_id"] for err in body["detail"])


def test_tc06_get_services_invalid_query_params(client: TestClient) -> None:
    """
    [TC06] Kiểm tra dữ liệu đầu vào không hợp lệ cho các tham số Query của danh sách dịch vụ.
    - Mục tiêu: Kiểm tra các ràng buộc:
      + skip >= 0 (skip âm -> 422)
      + limit >= 1 (limit <= 0 -> 422)
      + limit <= 200 (limit > 200 -> 422)
      + is_active phải là kiểu boolean
    - Kết quả mong đợi: HTTP 422 Unprocessable Entity.
    """
    # 1. skip < 0
    res_skip_neg = client.get("/api/services?skip=-1")
    assert res_skip_neg.status_code == 422
    assert any(
        err.get("loc") == ["query", "skip"] for err in res_skip_neg.json()["detail"]
    )

    # 2. limit < 1 (limit = 0)
    res_limit_zero = client.get("/api/services?limit=0")
    assert res_limit_zero.status_code == 422
    assert any(
        err.get("loc") == ["query", "limit"] for err in res_limit_zero.json()["detail"]
    )

    # 3. limit > 200 (limit = 201)
    res_limit_large = client.get("/api/services?limit=201")
    assert res_limit_large.status_code == 422
    assert any(
        err.get("loc") == ["query", "limit"] for err in res_limit_large.json()["detail"]
    )

    # 4. is_active không phải boolean
    res_bool_err = client.get("/api/services?is_active=khong_phai_boolean")
    assert res_bool_err.status_code == 422
    assert any(
        err.get("loc") == ["query", "is_active"]
        for err in res_bool_err.json()["detail"]
    )


def test_tc07_get_services_empty_search_result(client: TestClient) -> None:
    """
    [TC07] Trường hợp biên: Tìm kiếm từ khóa không tồn tại.
    - Mục tiêu: Kiểm tra phản hồi khi không có dịch vụ nào khớp với từ khóa tìm kiếm.
    - Dữ liệu kiểm thử: q="KHONG_TON_TAI_TRONG_HE_THONG_99999".
    - Kết quả mong đợi: HTTP 200 OK, 'data' là mảng rỗng [], 'count' = 0.
    """
    non_existent_keyword = f"NOT_FOUND_{uuid.uuid4().hex}"
    response = client.get(f"/api/services?q={non_existent_keyword}")

    assert response.status_code == 200
    result = response.json()
    assert result["data"] == []
    assert result["count"] == 0


def test_tc08_get_services_keyword_search_filters(
    client: TestClient, db: Session
) -> None:
    """
    [TC08] Kiểm tra tìm kiếm từ khóa theo tên, mã dịch vụ và mô tả (Case-insensitive & Trim).
    - Mục tiêu: Đảm bảo bộ lọc từ khóa 'q' tìm kiếm được:
      + Theo tên dịch vụ.
      + Theo mã dịch vụ.
      + Theo nội dung mô tả.
      + Không phân biệt chữ hoa, chữ thường.
      + Xử lý khoảng trắng thừa ở đầu và cuối từ khóa.
    - Kết quả mong đợi: HTTP 200 OK, chỉ các bản ghi phù hợp được trả về.
    """
    suffix = uuid.uuid4().hex[:6].upper()
    code = f"SVC-SEARCH-{suffix}"
    name = f"Ép Kính Cường Lực Gor {suffix}"
    description = f"Kính Gor nhập khẩu độ cứng 9H chống xước cao cấp {suffix}"

    svc = create_sample_service(
        db,
        code=code,
        name=name,
        description=description,
        is_active=True,
    )

    # 1. Tìm theo tên dịch vụ (kèm mã suffix chữ thường để test case-insensitivity)
    res_name = client.get(f"/api/services?q=Kính Cường Lực Gor {suffix.lower()}")
    assert res_name.status_code == 200
    ids_name = [item["id"] for item in res_name.json()["data"]]
    assert str(svc.id) in ids_name

    # 2. Tìm theo mã dịch vụ (chữ hoa/chữ thường hỗn hợp)
    res_code = client.get(f"/api/services?q={code.lower()}")
    assert res_code.status_code == 200
    ids_code = [item["id"] for item in res_code.json()["data"]]
    assert str(svc.id) in ids_code

    # 3. Tìm theo mô tả (từ khóa đặc biệt)
    res_desc = client.get("/api/services?q=độ cứng 9H")
    assert res_desc.status_code == 200
    ids_desc = [item["id"] for item in res_desc.json()["data"]]
    assert str(svc.id) in ids_desc

    # 4. Tìm với khoảng trắng thừa ở hai đầu
    res_trim = client.get(f"/api/services?q=%20%20{code}%20%20")
    assert res_trim.status_code == 200
    ids_trim = [item["id"] for item in res_trim.json()["data"]]
    assert str(svc.id) in ids_trim


def test_tc09_get_services_pagination(client: TestClient, db: Session) -> None:
    """
    [TC09] Kiểm tra phân trang danh mục dịch vụ (Pagination Boundary).
    - Mục tiêu: Kiểm tra hoạt động của tham số 'skip' và 'limit':
      + Tạo 5 dịch vụ có cùng tiền tố duy nhất.
      + Trang 1 (limit=2, skip=0): trả về 2 bản ghi, count=5.
      + Trang 2 (limit=2, skip=2): trả về 2 bản ghi tiếp theo, không trùng với trang 1.
      + Trang 3 (limit=2, skip=4): trả về 1 bản ghi còn lại.
      + Trang 4 (limit=2, skip=10): vượt quá tổng số lượng -> trả về mảng rỗng [], count=5.
    - Kết quả mong đợi: Phân trang chính xác, không trùng lặp và không sót bản ghi.
    """
    group_prefix = f"PAG-{uuid.uuid4().hex[:6].upper()}"
    created_services: list[Service] = []
    for i in range(5):
        svc = create_sample_service(
            db,
            code=f"SVC-{group_prefix}-{i:02d}",
            name=f"Dịch vụ Phân Trang {group_prefix} #{i + 1}",
            is_active=True,
        )
        created_services.append(svc)

    # Trang 1: limit=2, skip=0
    res_p1 = client.get(f"/api/services?q={group_prefix}&skip=0&limit=2")
    assert res_p1.status_code == 200
    p1_data = res_p1.json()
    assert p1_data["count"] == 5
    assert len(p1_data["data"]) == 2
    p1_ids = {x["id"] for x in p1_data["data"]}

    # Trang 2: limit=2, skip=2
    res_p2 = client.get(f"/api/services?q={group_prefix}&skip=2&limit=2")
    assert res_p2.status_code == 200
    p2_data = res_p2.json()
    assert p2_data["count"] == 5
    assert len(p2_data["data"]) == 2
    p2_ids = {x["id"] for x in p2_data["data"]}

    # Đảm bảo không trùng lặp giữa trang 1 và trang 2
    assert p1_ids.isdisjoint(p2_ids)

    # Trang 3: limit=2, skip=4
    res_p3 = client.get(f"/api/services?q={group_prefix}&skip=4&limit=2")
    assert res_p3.status_code == 200
    p3_data = res_p3.json()
    assert p3_data["count"] == 5
    assert len(p3_data["data"]) == 1
    p3_ids = {x["id"] for x in p3_data["data"]}
    assert p3_ids.isdisjoint(p1_ids)
    assert p3_ids.isdisjoint(p2_ids)

    # Trang 4: skip=10 vượt quá tổng số
    res_p4 = client.get(f"/api/services?q={group_prefix}&skip=10&limit=2")
    assert res_p4.status_code == 200
    p4_data = res_p4.json()
    assert p4_data["count"] == 5
    assert p4_data["data"] == []


def test_tc10_get_service_edge_case_zero_price(client: TestClient, db: Session) -> None:
    """
    [TC10] Trường hợp biên: Dịch vụ có giá khởi điểm bằng 0 (base_price = 0.0).
    - Mục tiêu: Kiểm tra các dịch vụ miễn phí (ví dụ: tư vấn kỹ thuật, vệ sinh máy miễn phí).
    - Kết quả mong đợi: HTTP 200 OK, base_price được lưu và trả về chính xác là 0.0.
    """
    svc = create_sample_service(
        db,
        name="Tư vấn và chẩn đoán lỗi phần cứng miễn phí",
        base_price=0.0,
        estimated_duration_minutes=15,
        is_active=True,
    )

    response = client.get(f"/api/services/{svc.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["base_price"] == 0.0
    assert data["id"] == str(svc.id)


def test_tc11_get_service_edge_case_null_description(
    client: TestClient, db: Session
) -> None:
    """
    [TC11] Trường hợp biên: Dịch vụ không có mô tả (description = None).
    - Mục tiêu: Đảm bảo hệ thống xử lý đúng trường hợp dịch vụ không có thông tin mô tả chi tiết.
    - Kết quả mong đợi: HTTP 200 OK, trường 'description' trả về null/None hợp lệ mà không phát sinh lỗi.
    """
    svc = create_sample_service(
        db,
        name="Dịch vụ không có mô tả",
        description=None,
        base_price=120_000.0,
        estimated_duration_minutes=20,
        is_active=True,
    )

    response = client.get(f"/api/services/{svc.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["description"] is None
    assert data["id"] == str(svc.id)


def test_tc12_get_service_edge_case_min_duration(
    client: TestClient, db: Session
) -> None:
    """
    [TC12] Trường hợp biên: Dịch vụ có thời gian sửa chữa tối thiểu (estimated_duration_minutes = 1).
    - Mục tiêu: Kiểm tra giá trị biên nhỏ nhất cho thời gian thực hiện dịch vụ.
    - Kết quả mong đợi: HTTP 200 OK, trường 'estimated_duration_minutes' trả về chính xác giá trị 1.
    """
    svc = create_sample_service(
        db,
        name="Dịch vụ thời gian ngắn 1 phút",
        base_price=50_000.0,
        estimated_duration_minutes=1,
        is_active=True,
    )

    response = client.get(f"/api/services/{svc.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["estimated_duration_minutes"] == 1


def test_tc13_get_services_default_hides_inactive_services(
    client: TestClient, db: Session
) -> None:
    """
    [TC13] Khách hàng mặc định không thấy dịch vụ đã bị ẩn (is_active = False).
    - Mục tiêu: Bảo đảm quy tắc nghiệp vụ dịch vụ ẩn không xuất hiện cho khách hàng.
    - Kết quả mong đợi: Danh sách trả về chỉ chứa dịch vụ đang kinh doanh (is_active=True).
    """
    suffix = uuid.uuid4().hex[:6].upper()
    active_code = f"SVC-ACT-{suffix}"
    hidden_code = f"SVC-HID-{suffix}"

    create_sample_service(db, code=active_code, is_active=True)
    create_sample_service(db, code=hidden_code, is_active=False)

    # Khách hàng gọi không kèm token
    response = client.get(f"/api/services?q={suffix}")
    assert response.status_code == 200
    data = response.json()

    codes = [item["code"] for item in data["data"]]
    assert active_code in codes
    assert hidden_code not in codes


def test_tc14_service_catalog_unit_get_service_by_id(db: Session) -> None:
    """
    [TC14] Unit Test tầng Service: Kiểm tra trực tiếp hàm get_service_by_id().
    - Mục tiêu: Kiểm tra logic tại service_catalog_service độc lập với HTTP router.
    - Trường hợp 1: Dịch vụ tồn tại -> Trả về ServicePublic.
    - Trường hợp 2: Dịch vụ không tồn tại -> Bắn ra HTTPException 404.
    """
    svc = create_sample_service(db, is_active=True)

    # 1. Dịch vụ tồn tại
    result = service_catalog_service.get_service_by_id(session=db, service_id=svc.id)
    assert result.id == svc.id
    assert result.code == svc.code
    assert result.name == svc.name

    # 2. Dịch vụ không tồn tại
    random_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc_info:
        service_catalog_service.get_service_by_id(session=db, service_id=random_id)
    assert exc_info.value.status_code == 404
    assert f"Không tìm thấy dịch vụ với ID {random_id}" in exc_info.value.detail


def test_tc15_service_catalog_unit_get_services(db: Session) -> None:
    """
    [TC15] Unit Test tầng Service: Kiểm tra trực tiếp hàm get_services().
    - Mục tiêu: Kiểm tra hàm truy vấn danh mục dịch vụ tại tầng nghiệp vụ:
      + Phân trang skip/limit.
      + Bộ lọc is_active.
      + Bộ lọc q.
    """
    suffix = uuid.uuid4().hex[:6].upper()
    svc1 = create_sample_service(
        db,
        code=f"SVC-U1-{suffix}",
        name=f"Unit Test Svc 1 {suffix}",
        is_active=True,
    )
    svc2 = create_sample_service(
        db,
        code=f"SVC-U2-{suffix}",
        name=f"Unit Test Svc 2 {suffix}",
        is_active=False,
    )

    # 1. Lấy tất cả theo từ khóa suffix
    items, total = service_catalog_service.get_services(
        session=db,
        skip=0,
        limit=10,
        is_active=None,
        q=suffix,
    )
    assert total == 2
    ids = [s.id for s in items]
    assert svc1.id in ids
    assert svc2.id in ids

    # 2. Chỉ lấy active
    items_active, total_active = service_catalog_service.get_services(
        session=db,
        skip=0,
        limit=10,
        is_active=True,
        q=suffix,
    )
    assert total_active == 1
    assert items_active[0].id == svc1.id

    # 3. Chỉ lấy inactive
    items_inactive, total_inactive = service_catalog_service.get_services(
        session=db,
        skip=0,
        limit=10,
        is_active=False,
        q=suffix,
    )
    assert total_inactive == 1
    assert items_inactive[0].id == svc2.id
