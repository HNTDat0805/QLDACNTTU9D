import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  ArrowRight,
  Bell,
  CalendarClock,
  FileText,
  LayoutDashboard,
  ShieldCheck,
} from "lucide-react"
import { AppointmentsService, RepairOrdersService } from "@/client"
import { DataState, dateTime, Status } from "@/components/Operations/shared"
import { getRoleLabel } from "@/components/Sidebar/roles"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import useAuth from "@/hooks/useAuth"
import { pageHead } from "@/lib/seo"

export const Route = createFileRoute("/_layout/app")({
  component: Dashboard,
  head: pageHead("Tổng quan"),
})

function Dashboard() {
  const { user: currentUser } = useAuth()
  const displayName = currentUser?.full_name || currentUser?.email || "bạn"
  const roleLabel = getRoleLabel(
    currentUser?.role ?? undefined,
    currentUser?.is_superuser,
  )
  const staff =
    currentUser?.is_superuser ||
    ["admin", "manager", "staff"].includes(currentUser?.role ?? "")
  const technician =
    !currentUser?.is_superuser && currentUser?.role === "technician"

  const activity = useQuery({
    queryKey: ["operations", "home", currentUser?.id],
    enabled: Boolean(currentUser),
    queryFn: async () =>
      staff
        ? (
            await AppointmentsService.readAppointmentsHistory({
              query: { limit: 6 },
            })
          ).data
        : technician
          ? (
              await RepairOrdersService.ordersReadRepairOrders({
                query: { limit: 6 },
              })
            ).data
          : (
              await AppointmentsService.readMyAppointments({
                query: { limit: 6 },
              })
            ).data,
  })

  return (
    <div className="space-y-6">
      {/* Figma Hero Greeting Card */}
      <Card className="overflow-hidden border-primary/15 bg-gradient-to-r from-card via-card to-primary/5 shadow-xs">
        <CardContent className="flex flex-wrap items-center justify-between gap-6 p-6 sm:p-8">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              FixPhone · {roleLabel}
            </span>
            <h1 className="mt-3 text-2xl font-bold tracking-tight sm:text-3xl">
              Xin chào, {displayName}
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground sm:text-base">
              Đây là khu vực làm việc an toàn của bạn trong hệ thống sửa chữa
              điện thoại. Sử dụng thanh điều hướng phía trên để chuyển nhanh
              giữa các phân hệ.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg" className="rounded-xl font-semibold">
              <Link
                to={
                  staff
                    ? "/workspace"
                    : technician
                      ? "/workspace/repairs"
                      : "/booking"
                }
              >
                <CalendarClock aria-hidden="true" className="size-4" />
                {staff
                  ? "Mở trung tâm tiếp nhận"
                  : technician
                    ? "Xem việc được phân công"
                    : "Đặt lịch sửa chữa"}
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="rounded-xl">
              <Link to="/quotes">
                <FileText aria-hidden="true" className="size-4" />
                Xem báo giá
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="rounded-xl">
              <Link to="/notifications">
                <Bell aria-hidden="true" className="size-4" />
                Thông báo
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Two-Column Figma Overview Grid */}
      <div className="grid gap-6 lg:grid-cols-[1.65fr_1fr]">
        <Card className="border-border/80 shadow-xs">
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <CardTitle className="text-lg">
              Hoạt động gần nhất · {activity.data?.count ?? 0} phiếu
            </CardTitle>
            <Button asChild variant="ghost" size="sm">
              <Link
                to={
                  staff
                    ? "/workspace/appointments"
                    : technician
                      ? "/workspace/repairs"
                      : "/appointments"
                }
              >
                Xem tất cả
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            <DataState
              pending={activity.isPending}
              error={activity.error}
              empty={!activity.data?.count}
            >
              <div className="divide-y rounded-xl border bg-background/60">
                {activity.data?.data.map((a) => (
                  <div
                    className="flex flex-wrap items-center justify-between gap-3 p-4 transition-colors hover:bg-muted/40"
                    key={a.id}
                  >
                    <div>
                      <p className="font-semibold text-foreground">
                        {a.appointment_number}
                      </p>
                      <p className="mt-0.5 text-sm text-muted-foreground">
                        {a.device?.brand
                          ? `${a.device.brand} ${a.device.model ?? ""} · `
                          : ""}
                        {dateTime(a.appointment_date)}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <Status value={a.status} />
                      {!staff && !technician && (
                        <Button asChild size="sm" variant="ghost">
                          <Link
                            to="/appointments/$appointmentId"
                            params={{ appointmentId: a.id }}
                          >
                            Chi tiết
                          </Link>
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </DataState>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="border-border/80 shadow-xs">
            <CardHeader className="flex-row items-center gap-3 space-y-0">
              <span className="rounded-xl bg-primary/10 p-2.5 text-primary">
                <LayoutDashboard aria-hidden="true" className="size-5" />
              </span>
              <CardTitle className="text-lg">
                {staff
                  ? "Điều hành cửa hàng"
                  : technician
                    ? "Công việc kỹ thuật"
                    : "Lịch hẹn và sửa chữa của bạn"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-muted-foreground">
              <p>
                {staff
                  ? "Quản lý lịch hẹn, tiếp nhận thiết bị tại quầy, điều phối hàng chờ, lập hóa đơn và đối soát doanh thu."
                  : technician
                    ? "Cập nhật kết quả chẩn đoán, lập báo giá linh kiện và ghi nhận tiến độ sửa chữa theo từng phiếu được giao."
                    : "Theo dõi tiến độ sửa chữa theo thời gian thực, duyệt báo giá chi tiết và xem lịch sử hóa đơn minh bạch."}
              </p>
              <div className="grid gap-2">
                {staff ? (
                  <>
                    <Button
                      asChild
                      variant="outline"
                      className="justify-between"
                    >
                      <Link to="/workspace/appointments">
                        Quản lý lịch hẹn
                        <ArrowRight aria-hidden="true" className="size-4" />
                      </Link>
                    </Button>
                    <Button
                      asChild
                      variant="outline"
                      className="justify-between"
                    >
                      <Link to="/workspace/intake">
                        Tiếp nhận thiết bị
                        <ArrowRight aria-hidden="true" className="size-4" />
                      </Link>
                    </Button>
                    <Button
                      asChild
                      variant="outline"
                      className="justify-between"
                    >
                      <Link to="/invoices">
                        Hóa đơn & thanh toán
                        <ArrowRight aria-hidden="true" className="size-4" />
                      </Link>
                    </Button>
                  </>
                ) : technician ? (
                  <>
                    <Button
                      asChild
                      variant="outline"
                      className="justify-between"
                    >
                      <Link to="/workspace/repairs">
                        Phiếu được phân công
                        <ArrowRight aria-hidden="true" className="size-4" />
                      </Link>
                    </Button>
                    <Button
                      asChild
                      variant="outline"
                      className="justify-between"
                    >
                      <Link to="/workspace/technicians">
                        Ca làm việc kỹ thuật
                        <ArrowRight aria-hidden="true" className="size-4" />
                      </Link>
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      asChild
                      variant="outline"
                      className="justify-between"
                    >
                      <Link to="/appointments">
                        Lịch hẹn của tôi
                        <ArrowRight aria-hidden="true" className="size-4" />
                      </Link>
                    </Button>
                    <Button
                      asChild
                      variant="outline"
                      className="justify-between"
                    >
                      <Link to="/invoices">
                        Hóa đơn & biên lai
                        <ArrowRight aria-hidden="true" className="size-4" />
                      </Link>
                    </Button>
                  </>
                )}
              </div>
            </CardContent>
          </Card>

          <div className="flex items-start gap-3 rounded-xl border bg-card/80 p-4 text-sm text-muted-foreground shadow-2xs">
            <ShieldCheck
              aria-hidden="true"
              className="mt-0.5 size-5 shrink-0 text-primary"
            />
            <p>
              Quyền truy cập của bạn được Backend xác minh. Việc ẩn mục điều
              hướng chỉ giúp giao diện gọn hơn, không thay thế kiểm soát quyền ở
              máy chủ.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
