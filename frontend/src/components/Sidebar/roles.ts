const roleLabels: Record<string, string> = {
  customer: "Khách hàng",
  staff: "Nhân viên",
  technician: "Kỹ thuật viên",
  manager: "Quản lý",
  admin: "Quản trị viên",
}

export function getRoleLabel(role: string | undefined, isSuperuser = false) {
  if (isSuperuser) return "Quản trị viên"
  return role && roleLabels[role] ? roleLabels[role] : "Tài khoản"
}
