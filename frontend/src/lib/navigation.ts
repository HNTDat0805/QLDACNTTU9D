import type { UserPublic } from "@/client"
import { getRoleLabel } from "@/components/Sidebar/roles"

export interface NavItem {
  title: string
  path: string
  exact?: boolean
}

export function getNavItemsForUser(
  user: UserPublic | null | undefined,
  loggedIn: boolean,
): NavItem[] {
  if (!loggedIn) {
    return [
      { title: "Trang chủ", path: "/", exact: true },
      { title: "Dịch vụ", path: "/services" },
      { title: "Đặt lịch", path: "/booking" },
      { title: "Giới thiệu", path: "/about" },
    ]
  }

  // Khi đã đăng nhập: nếu user chưa load (mock test token), mặc định role nhân viên có Tổng quan
  const role = user ? (user.role ?? "customer") : "staff"
  const isSuper = Boolean(user?.is_superuser)

  if (isSuper || role === "admin" || role === "manager") {
    const managerItems: NavItem[] = [
      { title: "Tổng quan", path: "/app", exact: true },
      { title: "Trung tâm tiếp nhận", path: "/workspace", exact: true },
      { title: "Lịch hẹn", path: "/workspace/appointments" },
      { title: "Tiếp nhận", path: "/workspace/intake" },
      { title: "Hàng chờ", path: "/workspace/queue" },
      { title: "Công việc", path: "/workspace/repairs" },
      { title: "Khách hàng", path: "/workspace/customers" },
      { title: "Dịch vụ", path: "/workspace/services" },
      { title: "Kỹ thuật viên", path: "/workspace/technicians" },
      { title: "Hóa đơn", path: "/invoices" },
      { title: "Báo cáo", path: "/workspace/reports" },
    ]
    if (isSuper || role === "admin") {
      managerItems.push({ title: "Tài khoản", path: "/admin" })
    }
    return managerItems
  }

  if (role === "staff") {
    return [
      { title: "Tổng quan", path: "/app", exact: true },
      { title: "Trung tâm tiếp nhận", path: "/workspace", exact: true },
      { title: "Tiếp nhận", path: "/workspace/intake" },
      { title: "Hàng chờ", path: "/workspace/queue" },
      { title: "Lịch hẹn", path: "/workspace/appointments" },
      { title: "Phiếu sửa chữa", path: "/workspace/repairs" },
      { title: "Báo giá", path: "/quotes" },
      { title: "Hóa đơn", path: "/invoices" },
      { title: "Khách hàng", path: "/workspace/customers" },
      { title: "Kỹ thuật viên", path: "/workspace/technicians" },
    ]
  }

  if (role === "technician") {
    return [
      { title: "Tổng quan", path: "/app", exact: true },
      { title: "Công việc", path: "/workspace/repairs" },
      { title: "Lịch hẹn", path: "/workspace/appointments" },
      { title: "Hàng chờ", path: "/workspace/queue" },
      { title: "Báo giá", path: "/quotes" },
      { title: "Ca làm việc", path: "/workspace/technicians" },
    ]
  }

  // Khách hàng (Customer) - Đã có Trang chủ thì không cần Tổng quan nữa
  return [
    { title: "Trang chủ", path: "/", exact: true },
    { title: "Dịch vụ", path: "/services" },
    { title: "Đặt lịch", path: "/booking" },
    { title: "Lịch hẹn của tôi", path: "/appointments" },
    { title: "Báo giá", path: "/quotes" },
    { title: "Hóa đơn", path: "/invoices" },
    { title: "Đánh giá", path: "/reviews" },
  ]
}

export function getBrandDestination(
  user: UserPublic | null | undefined,
  loggedIn: boolean,
): string {
  if (!loggedIn || !user) return "/"
  const role = user.role ?? "customer"
  if (role === "customer" && !user.is_superuser) return "/"
  return "/app"
}

export function getUserRoleLabel(
  user: UserPublic | null | undefined,
  loggedIn: boolean,
): string {
  if (!loggedIn || !user) return ""
  return getRoleLabel(user.role ?? undefined, user.is_superuser)
}
