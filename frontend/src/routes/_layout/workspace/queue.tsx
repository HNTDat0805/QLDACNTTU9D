import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { useState } from "react"
import { QueueService, ServicesService } from "@/client"
import {
  ActionForm,
  DataState,
  dateTime,
  Pager,
  PageTitle,
  Panel,
  Status,
} from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
export const Route = createFileRoute("/_layout/workspace/queue")({
  component: Queue,
})
function Queue() {
  const [date, setDate] = useState("")
  const [page, setPage] = useState(0)
  const services = useQuery({
    queryKey: ["services"],
    queryFn: async () => (await ServicesService.readPublicServices()).data,
  })
  const queue = useQuery({
    queryKey: ["operations", "queue", date, page],
    queryFn: async () =>
      (
        await QueueService.readQueue({
          query: { date: date || undefined, skip: page * 20, limit: 20 },
        })
      ).data,
  })
  return (
    <section>
      <PageTitle
        title="Hàng chờ tiếp nhận"
        description="Thứ tự theo thời gian hẹn và thời điểm tạo."
      >
        <Button asChild>
          <Link to="/workspace/appointments">Xử lý lịch hẹn</Link>
        </Button>
      </PageTitle>
      <div className="mb-6">
        <Panel title="Đặt chỗ nhanh">
          <ActionForm
            fields={[
              { name: "name", label: "Tên khách", required: true },
              {
                name: "phone",
                label: "Số điện thoại khách",
                type: "tel",
                required: true,
              },
              {
                name: "service",
                label: "Dịch vụ",
                required: true,
                options:
                  services.data?.data.map((s) => ({
                    value: s.id,
                    label: s.name,
                  })) ?? [],
              },
              {
                name: "date",
                label: "Ngày đặt chỗ",
                type: "date",
                required: true,
              },
              {
                name: "time",
                label: "Giờ đặt chỗ",
                type: "time",
                required: true,
              },
            ]}
            submitLabel="Thêm vào hàng chờ"
            onSubmit={(v) =>
              QueueService.addAppointmentToQueue({
                body: {
                  customer_name: v.name,
                  customer_phone: v.phone,
                  service_id: v.service,
                  appointment_date: v.date,
                  start_time: v.time,
                },
              })
            }
          />
        </Panel>
      </div>
      <Input
        className="mb-5 max-w-xs"
        aria-label="Ngày hàng chờ"
        type="date"
        value={date}
        onChange={(e) => {
          setDate(e.target.value)
          setPage(0)
        }}
      />
      <DataState
        pending={queue.isPending}
        error={queue.error}
        empty={!queue.data?.count}
      >
        <ol className="space-y-3">
          {queue.data?.data.map((a) => (
            <li
              key={a.appointment_id}
              className="flex flex-wrap items-center gap-4 rounded-xl border bg-card p-4"
            >
              <span className="flex size-10 items-center justify-center rounded-full bg-primary/10 font-bold text-primary">
                {a.queue_position}
              </span>
              <div className="flex-1">
                <p className="font-semibold">
                  {a.customer_name} · {a.appointment_number}
                </p>
                <p className="text-sm text-muted-foreground">
                  {a.device_info} · {dateTime(a.appointment_date)}
                </p>
                <p className="text-sm">
                  {a.technician_name || "Chưa phân công"}
                </p>
              </div>
              <Status value={a.status} />
            </li>
          ))}
        </ol>
      </DataState>
      <Pager page={page} count={queue.data?.count ?? 0} setPage={setPage} />
    </section>
  )
}
