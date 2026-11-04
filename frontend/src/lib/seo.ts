/**
 * Thông tin thương hiệu và helper tạo tiêu đề tab trình duyệt.
 * Mọi route dùng `pageHead` để tiêu đề luôn theo định dạng thống nhất:
 *   "<Tên trang> | FixPhone"
 */
export const APP_NAME = "FixPhone"
export const APP_TAGLINE = "Quản lý sửa chữa điện thoại"
export const APP_DESCRIPTION =
  "FixPhone là hệ thống hỗ trợ đặt lịch, tiếp nhận thiết bị và theo dõi quy trình sửa chữa điện thoại minh bạch."

export function formatPageTitle(title?: string): string {
  return title ? `${title} | ${APP_NAME}` : `${APP_NAME} | ${APP_TAGLINE}`
}

/** Trả về hàm `head` cho TanStack Router với title (và description nếu có). */
export function pageHead(title?: string, description?: string) {
  return () => ({
    meta: [
      { title: formatPageTitle(title) },
      ...(description ? [{ name: "description", content: description }] : []),
    ],
  })
}
