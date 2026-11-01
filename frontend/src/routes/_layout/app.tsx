import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { LayoutDashboard, ShieldCheck } from "lucide-react"
import { AppointmentsService, RepairOrdersService } from "@/client"
import { DataState, dateTime, Status } from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/app")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "Khu vực làm việc | FixCare",
      },
    ],
  }),
})

function Dashboard() {
  const { user: currentUser } = useAuth()
  const displayName = currentUser?.full_name || currentUser?.email || "bạn"
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
              query: { limit: 5 },
            })
          ).data
        : technician
          ? (
              await RepairOrdersService.ordersReadRepairOrders({
                query: { limit: 5 },
              })
            ).data
          : (
              await AppointmentsService.readMyAppointments({
                query: { limit: 5 },
              })
            ).data,
  })

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <div>
        <p className="text-sm font-medium text-primary">FixCare</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
          Xin chào, {displayName}
        </h1>
        <p className="mt-2 text-muted-foreground">
          Đây là khu vực làm việc an toàn của bạn trong hệ thống sửa chữa điện
          thoại.
        </p>
      </div>

      <Card>
        <CardHeader className="flex-row items-center gap-3 space-y-0">
          <span className="rounded-lg bg-primary/10 p-2 text-primary">
            <LayoutDashboard aria-hidden="true" className="size-5" />
          </span>
          <CardTitle>
            {staff
              ? "Điều hành cửa hàng"
              : technician
                ? "Công việc kỹ thuật"
                : "Lịch hẹn và sửa chữa của bạn"}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          <div className="flex flex-wrap gap-3">
            <Button asChild>
              <Link
                to={
                  staff
                    ? "/workspace"
                    : technician
                      ? "/workspace/repairs"
                      : "/booking"
                }
              >
                {staff
                  ? "Mở trung tâm tiếp nhận"
                  : technician
                    ? "Xem việc được phân công"
                    : "Đặt lịch sửa chữa"}
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/quotes">Xem báo giá</Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/notifications">Thông báo</Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            Hoạt động gần nhất · {activity.data?.count ?? 0} phiếu
          </CardTitle>
        </CardHeader>
        <CardContent>
          <DataState
            pending={activity.isPending}
            error={activity.error}
            empty={!activity.data?.count}
          >
            <div className="space-y-3">
              {activity.data?.data.map((a) => (
                <div
                  className="flex flex-wrap justify-between gap-3 border-b pb-3"
                  key={a.id}
                >
                  <div>
                    <p className="font-medium">{a.appointment_number}</p>
                    <p className="text-sm text-muted-foreground">
                      {dateTime(a.appointment_date)}
                    </p>
                  </div>
                  <Status value={a.status} />
                </div>
              ))}
            </div>
          </DataState>
        </CardContent>
      </Card>

      <div className="flex items-start gap-3 rounded-xl border bg-muted/40 p-4 text-sm text-muted-foreground">
        <ShieldCheck aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
        <p>
          Quyền truy cập của bạn được Backend xác minh. Việc ẩn mục điều hướng
          chỉ giúp giao diện gọn hơn, không thay thế kiểm soát quyền ở máy chủ.
        </p>
      </div>
    </div>
  )
}
