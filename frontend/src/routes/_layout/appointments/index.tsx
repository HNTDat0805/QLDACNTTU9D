import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { useState } from "react"
import { AppointmentsService } from "@/client"
import {
  dateTime,
  Pager,
  PageTitle,
  Status,
} from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { getApiErrorMessage } from "@/utils"

export const Route = createFileRoute("/_layout/appointments/")({
  component: MyAppointments,
})

function MyAppointments() {
  const [page, setPage] = useState(0)
  const appointments = useQuery({
    queryKey: ["my-appointments", page],
    queryFn: async () =>
      (
        await AppointmentsService.readMyAppointments({
          query: { skip: page * 20, limit: 20 },
        })
      ).data,
  })
  if (appointments.isLoading) return <p>Đang tải lịch hẹn...</p>
  if (appointments.error)
    return <p role="alert">{getApiErrorMessage(appointments.error)}</p>
  return (
    <section className="space-y-5">
      <PageTitle
        title="Lịch hẹn của tôi"
        description="Xem thời gian, tiến độ và các thao tác được phép cho lịch sửa chữa."
      >
        <Button asChild>
          <Link to="/booking">Đặt lịch mới</Link>
        </Button>
      </PageTitle>
      {appointments.data?.data.length === 0 ? (
        <Card>
          <CardContent>Bạn chưa có lịch hẹn nào.</CardContent>
        </Card>
      ) : (
        appointments.data?.data.map((appointment) => (
          <Card key={appointment.id}>
            <CardContent className="flex flex-wrap items-center justify-between gap-4 py-5">
              <div>
                <p className="font-semibold">
                  {appointment.appointment_number}
                </p>
                <p className="text-sm text-muted-foreground">
                  {dateTime(appointment.appointment_date)}
                </p>
                <p className="mt-1 text-sm">
                  {appointment.services?.map((s) => s.service_name).join(", ")}
                </p>
              </div>
              <Status value={appointment.status} />
              <Button asChild variant="outline">
                <Link
                  to="/appointments/$appointmentId"
                  params={{ appointmentId: appointment.id }}
                >
                  Xem chi tiết
                </Link>
              </Button>
            </CardContent>
          </Card>
        ))
      )}
      <Pager
        page={page}
        count={appointments.data?.count ?? 0}
        setPage={setPage}
      />
    </section>
  )
}
