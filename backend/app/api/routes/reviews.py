import uuid

from fastapi import APIRouter, Path, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    ReviewCreateRequest,
    ReviewPublic,
    ReviewsPublic,
)
from app.services import review_service

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post(
    "",
    response_model=ReviewPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Gửi đánh giá chất lượng dịch vụ sửa chữa (Task 393)",
    description="""
API tiếp nhận đánh giá từ khách hàng cho dịch vụ sửa chữa:
- Tiếp nhận điểm đánh giá (1-5 sao) và nhận xét của khách hàng.
- Kiểm tra điều kiện nghiệp vụ: Chỉ cho phép đánh giá lịch hẹn đã hoàn thành (`COMPLETED`).
- Kiểm tra quyền: Chỉ khách hàng sở hữu lịch hẹn (hoặc Quản trị viên) mới có quyền gửi đánh giá.
- Ngăn chặn đánh giá trùng lặp: Mỗi lịch hẹn chỉ được đánh giá duy nhất một lần.
- Tự động liên kết đánh giá với khách hàng và kỹ thuật viên tương ứng từ lịch hẹn.
""",
)
def create_service_review(
    session: SessionDep,
    current_user: CurrentUser,
    body: ReviewCreateRequest,
) -> ReviewPublic:
    return review_service.create_review(
        session=session,
        data=body,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=ReviewsPublic,
    status_code=status.HTTP_200_OK,
    summary="Truy xuất danh sách đánh giá dịch vụ (Task 393)",
    description="""
API lấy danh sách các đánh giá dịch vụ:
- Hỗ trợ phân trang bằng `skip` và `limit`.
- Hỗ trợ lọc theo `service_id`, `appointment_id`, hoặc điểm đánh giá `rating`.
- Trả về danh sách chi tiết, tổng số lượng đánh giá và điểm trung bình (`average_rating`).
""",
)
def get_service_reviews(
    session: SessionDep,
    skip: int = Query(default=0, ge=0, description="Vị trí bắt đầu"),
    limit: int = Query(default=20, ge=1, le=100, description="Số lượng bản ghi tối đa"),
    service_id: uuid.UUID | None = Query(
        default=None, description="Lọc theo mã định danh dịch vụ sửa chữa"
    ),
    appointment_id: uuid.UUID | None = Query(
        default=None, description="Lọc theo mã lịch hẹn sửa chữa"
    ),
    rating: int | None = Query(
        default=None, ge=1, le=5, description="Lọc theo điểm đánh giá (1-5 sao)"
    ),
) -> ReviewsPublic:
    return review_service.get_reviews(
        session=session,
        skip=skip,
        limit=limit,
        service_id=service_id,
        appointment_id=appointment_id,
        rating=rating,
    )


@router.get(
    "/{review_id}",
    response_model=ReviewPublic,
    status_code=status.HTTP_200_OK,
    summary="Truy xuất chi tiết đánh giá (Task 393)",
    description="Lấy thông tin chi tiết của một đánh giá cụ thể qua ID.",
)
def get_service_review_detail(
    session: SessionDep,
    review_id: uuid.UUID = Path(..., description="Mã định danh duy nhất của đánh giá"),
) -> ReviewPublic:
    return review_service.get_review_by_id(
        session=session,
        review_id=review_id,
    )
