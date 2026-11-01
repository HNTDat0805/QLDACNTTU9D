import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { CalendarCheck, ClipboardList, Clock, Users } from "lucide-react"
import { AppointmentsService, CustomersService, QueueService } from "@/client"
import { DataState, PageTitle } from "@/components/Operations/shared"
import { Card, CardContent } from "@/components/ui/card"

export const Route = createFileRoute("/_layout/workspace/")({
  component: StaffDashboard,
})
function StaffDashboard() {
  const data = useQuery({
    queryKey: ["operations", "dashboard"],
    queryFn: async () => {
      const [pending, confirmed, queue, customers] = await Promise.all([
        AppointmentsService.readAppointmentsHistory({
          query: { status: "PENDING", limit: 1 },
        }),
        AppointmentsService.readAppointmentsHistory({
          query: { status: "CONFIRMED", limit: 1 },
        }),
        QueueService.readQueue({ query: { limit: 1 } }),
        CustomersService.readCustomers({ query: { limit: 1 } }),
      ])
      return [
        pending.data.count,
        confirmed.data.count,
        queue.data.count,
        customers.data.count,
      ]
    },
  })
  const cards = [
    { title: "Chờ xác nhận", icon: Clock, to: "/workspace/appointments" },
    {
      title: "Lịch đã xác nhận",
      icon: CalendarCheck,
      to: "/workspace/appointments",
    },
    { title: "Trong hàng chờ", icon: ClipboardList, to: "/workspace/queue" },
    { title: "Khách hàng", icon: Users, to: "/workspace/customers" },
  ]
  return (
    <section>
      <PageTitle
        title="Trung tâm tiếp nhận"
        description="Lịch hẹn, hàng chờ và khách hàng — dữ liệu được cập nhật từ hệ thống."
      />
      <DataState pending={data.isPending} error={data.error}>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {cards.map((card, index) => (
            <Link
              key={card.title}
              to={card.to}
              className="rounded-xl focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Card className="h-full transition-colors hover:border-primary/50">
                <CardContent className="p-6">
                  <card.icon className="mb-4 size-5 text-primary" />
                  <p className="text-sm text-muted-foreground">{card.title}</p>
                  <p className="mt-2 text-3xl font-bold">
                    {data.data?.[index]}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </DataState>
    </section>
  )
}
