import uuid

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, RequireStaff, SessionDep
from app.models import (
    Appointment,
    QuotationAcceptRequest,
    QuotationCreate,
    QuotationResponse,
    QuotationsPublic,
    Quote,
    RepairStatusHistory,
    get_datetime_utc,
)
from app.services import access_service, quote_service

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.get("", response_model=QuotationsPublic)
def read_quotations(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    appointment_id: uuid.UUID | None = None,
) -> QuotationsPublic:
    ids = access_service.accessible_appointment_ids(session, current_user)
    query = select(Quote)
    count = select(func.count()).select_from(Quote)
    if ids is not None:
        query = query.where(col(Quote.appointment_id).in_(ids))
        count = count.where(col(Quote.appointment_id).in_(ids))
    if appointment_id:
        query = query.where(Quote.appointment_id == appointment_id)
        count = count.where(Quote.appointment_id == appointment_id)
    rows = session.exec(
        query.order_by(col(Quote.created_at).desc()).offset(skip).limit(limit)
    ).all()
    return QuotationsPublic(
        data=[quote_service._build_quotation_detail(session, quote) for quote in rows],
        count=session.exec(count).one(),
    )


@router.get("/{quote_id}", response_model=QuotationResponse)
def read_quotation(
    session: SessionDep, current_user: CurrentUser, quote_id: uuid.UUID
) -> QuotationResponse:
    quote = session.get(Quote, quote_id)
    appointment = session.get(Appointment, quote.appointment_id) if quote else None
    if not quote or not appointment:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo giá")
    access_service.check_appointment_access(session, current_user, appointment)
    return QuotationResponse(
        message="Chi tiết báo giá",
        data=quote_service._build_quotation_detail(session, quote),
    )


@router.post("/{quote_id}/reject", response_model=QuotationResponse)
def reject_quotation(
    session: SessionDep,
    current_user: CurrentUser,
    quote_id: uuid.UUID,
    body: QuotationAcceptRequest,
) -> QuotationResponse:
    quote = session.exec(
        select(Quote).where(Quote.id == quote_id).with_for_update()
    ).first()
    appointment = session.get(Appointment, quote.appointment_id) if quote else None
    if not quote or not appointment:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo giá")
    access_service.check_appointment_access(session, current_user, appointment)
    if quote.status not in ("DRAFT", "SENT"):
        raise HTTPException(
            status_code=409, detail="Báo giá không còn được phép từ chối"
        )
    quote.status = "REJECTED"
    quote.updated_at = get_datetime_utc()
    session.add(quote)
    session.add(
        RepairStatusHistory(
            appointment_id=appointment.id,
            previous_status=appointment.status,
            new_status=appointment.status,
            changed_by_user_id=current_user.id,
            note=f"Từ chối báo giá {quote.quote_number}: {body.note or ''}",
        )
    )
    session.commit()
    session.refresh(quote)
    return QuotationResponse(
        message="Đã từ chối báo giá",
        data=quote_service._build_quotation_detail(session, quote),
    )


@router.post(
    "",
    response_model=QuotationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo báo giá sửa chữa mới",
    description="""
API tạo báo giá sửa chữa cho một phiếu sửa chữa (Appointment):
- Nhận định danh phiếu sửa chữa qua `appointment_id` hoặc `appointment_number`.
- Nhận danh sách các hạng mục báo giá (dịch vụ có sẵn hoặc hạng mục tùy biến linh kiện/công thợ).
- Xác minh phiếu sửa chữa đang ở trạng thái hợp lệ để báo giá (chưa bị hủy hoặc đã hoàn thành).
- Tự động tính toán thành tiền từng hạng mục và tổng tiền ở backend (tránh sai số số thực).
- Khởi tạo trạng thái báo giá (mặc định là `DRAFT`).
- Gắn mã báo giá duy nhất (ví dụ: `QUO-YYYYMMDD-XXXX`).
- Lưu trữ an toàn bằng transaction.
- Quyền truy cập: Nhân viên cửa hàng (`RequireStaff`: Admin, Manager, Staff, Technician).
""",
)
def create_quotation(
    session: SessionDep,
    current_user: RequireStaff,
    body: QuotationCreate,
) -> QuotationResponse:
    detail = quote_service.create_repair_quotation(
        session=session,
        quote_in=body,
        current_user=current_user,
    )
    return QuotationResponse(
        success=True,
        message=f"Tạo báo giá sửa chữa {detail.quote_number} thành công",
        data=detail,
    )


@router.post(
    "/{quote_id}/accept",
    response_model=QuotationResponse,
    status_code=status.HTTP_200_OK,
    summary="Duyệt báo giá sửa chữa",
    description="""
API duyệt báo giá sửa chữa (Quotation Approval):
- Nhận `quote_id` của báo giá cần duyệt.
- Kiểm tra báo giá tồn tại và đang ở trạng thái cho phép duyệt (`DRAFT` hoặc `SENT`).
- Từ chối duyệt nếu báo giá đã được duyệt trước đó (`ACCEPTED`) hoặc đã bị từ chối (`REJECTED`) với mã lỗi `409 Conflict`.
- Phân quyền:
  + Khách hàng (`customer`): Chỉ được duyệt báo giá thuộc phiếu sửa chữa của chính mình.
  + Nhân viên (`staff`, `technician`, `manager`, `admin`): Có quyền duyệt báo giá khi được khách hàng đồng ý trực tiếp/qua điện thoại.
- Khóa dòng bi quan (`with_for_update`) nhằm xử lý an toàn tình huống hai yêu cầu duyệt đồng thời hoặc cạnh tranh trạng thái.
- Cập nhật trạng thái báo giá sang `ACCEPTED` và ghi nhận nhật ký kiểm toán vào `repair_status_history`.
- Không tự ý thay đổi trạng thái sửa chữa của phiếu sửa chữa.
""",
)
def accept_quotation(
    session: SessionDep,
    current_user: CurrentUser,
    quote_id: uuid.UUID = Path(..., description="ID của báo giá cần duyệt"),
    body: QuotationAcceptRequest | None = None,
) -> QuotationResponse:
    note = body.note if body else None
    detail = quote_service.accept_quotation(
        session=session,
        quote_id=quote_id,
        current_user=current_user,
        note=note,
    )
    return QuotationResponse(
        success=True,
        message=f"Duyệt báo giá {detail.quote_number} thành công",
        data=detail,
    )


@router.post(
    "/{quote_id}/approve",
    response_model=QuotationResponse,
    status_code=status.HTTP_200_OK,
    summary="Duyệt báo giá sửa chữa (Alias)",
    description="Endpoint bí danh trỏ tới cùng luồng xử lý duyệt báo giá sửa chữa.",
)
def approve_quotation_alias(
    session: SessionDep,
    current_user: CurrentUser,
    quote_id: uuid.UUID = Path(..., description="ID của báo giá cần duyệt"),
    body: QuotationAcceptRequest | None = None,
) -> QuotationResponse:
    return accept_quotation(
        session=session,
        current_user=current_user,
        quote_id=quote_id,
        body=body,
    )
