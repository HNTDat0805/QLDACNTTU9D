import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { useState } from "react"

import { AppointmentsService, SlotsService } from "@/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { getApiErrorMessage } from "@/utils"

export const Route = createFileRoute("/_layout/appointments/$appointmentId")({
  component: AppointmentDetail,
})

const mutableStatuses = new Set(["PENDING", "CONFIRMED"])

function AppointmentDetail() {
  const { appointmentId } = Route.useParams()
  const queryClient = useQueryClient()
  const [reason, setReason] = useState("")
  const [date, setDate] = useState("")
  const [time, setTime] = useState("")
  const [notice, setNotice] = useState("")
  const [cancelOpen, setCancelOpen] = useState(false)
  const detail = useQuery({
    queryKey: ["appointment", appointmentId],
    queryFn: async () =>
      (
        await AppointmentsService.readAppointmentDetail({
          path: { appointment_id: appointmentId },
        })
      ).data,
  })
  const serviceId = detail.data?.services?.[0]?.service_id
  const slots = useQuery({
    queryKey: ["reschedule-slots", serviceId, date],
    enabled: Boolean(serviceId && date),
    queryFn: async () =>
      (
        await SlotsService.getAvailableSlots({
          query: { service_id: serviceId ?? "", date },
        })
      ).data,
  })
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["my-appointments"] })
  const cancel = useMutation({
    mutationFn: () =>
      AppointmentsService.cancelAppointment({
        path: { appointment_id: appointmentId },
        body: { reason },
      }),
    onSuccess: () => {
      setNotice("Đã hủy lịch thành công")
      setCancelOpen(false)
      invalidate()
      detail.refetch()
    },
  })
  const reschedule = useMutation({
    mutationFn: () =>
      AppointmentsService.updateAppointment({
        path: { appointment_id: appointmentId },
        body: {
          appointment_date: date,
          start_time: time,
          reschedule_reason: reason || undefined,
        },
      }),
    onSuccess: () => {
      setNotice("Đã đổi lịch thành công")
      invalidate()
      detail.refetch()
    },
  })
  if (detail.isLoading)
    return <p className="text-muted-foreground">Đang tải lịch hẹn...</p>
  if (detail.error || !detail.data)
    return (
      <p role="alert" className="text-destructive">
        {getApiErrorMessage(detail.error)}
      </p>
    )
  const canChange = mutableStatuses.has(detail.data.status)
  const error = cancel.error || reschedule.error || slots.error
  return (
    <section className="space-y-6" aria-labelledby="appointment-title">
      <Button asChild variant="ghost">
        <Link to="/appointments">← Lịch hẹn của tôi</Link>
      </Button>
      <Card>
        <CardHeader>
          <CardTitle id="appointment-title">
            {detail.data.appointment_number}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p>
            <strong>Trạng thái:</strong> {detail.data.status}
          </p>
          <p>
            <strong>Thời gian:</strong>{" "}
            {new Date(detail.data.appointment_date).toLocaleString("vi-VN")}
          </p>
          <p>
            <strong>Dịch vụ:</strong>{" "}
            {(detail.data.services ?? [])
              .map((service) => service.service_name)
              .join(", ")}
          </p>
          {detail.data.device && (
            <p>
              <strong>Thiết bị:</strong> {detail.data.device.brand}{" "}
              {detail.data.device.model}
            </p>
          )}
        </CardContent>
      </Card>
      {canChange && (
        <Card>
          <CardHeader>
            <CardTitle>Đổi hoặc hủy lịch</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="reschedule-date">Ngày mới</Label>
              <Input
                id="reschedule-date"
                type="date"
                value={date}
                onChange={(event) => {
                  setDate(event.target.value)
                  setTime("")
                }}
              />
            </div>
            {date && (
              <div className="flex flex-wrap gap-2">
                {slots.data?.available_slots.map((slot) => (
                  <Button
                    key={slot.start_time}
                    type="button"
                    variant={time === slot.start_time ? "default" : "outline"}
                    disabled={!slot.available}
                    onClick={() => setTime(slot.start_time)}
                  >
                    {slot.start_time}
                  </Button>
                ))}
              </div>
            )}
            <div className="grid gap-2">
              <Label htmlFor="appointment-reason">
                Lý do thay đổi hoặc hủy
              </Label>
              <Input
                id="appointment-reason"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
            </div>
            <div className="flex flex-wrap gap-3">
              <Button
                disabled={
                  !date || !time || reschedule.isPending || cancel.isPending
                }
                onClick={() => reschedule.mutate()}
              >
                Đổi lịch
              </Button>
              <Button
                variant="destructive"
                disabled={
                  !reason.trim() || cancel.isPending || reschedule.isPending
                }
                onClick={() => setCancelOpen(true)}
              >
                Hủy lịch
              </Button>
              <Dialog open={cancelOpen} onOpenChange={setCancelOpen}>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Xác nhận hủy lịch?</DialogTitle>
                  </DialogHeader>
                  <p>
                    Bạn muốn hủy lịch {detail.data.appointment_number}? Lý do:{" "}
                    {reason}
                  </p>
                  <Button
                    variant="destructive"
                    disabled={cancel.isPending}
                    onClick={() => cancel.mutate()}
                  >
                    Xác nhận hủy
                  </Button>
                </DialogContent>
              </Dialog>
            </div>
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {getApiErrorMessage(error)}
              </p>
            )}
          </CardContent>
        </Card>
      )}
      {notice && (
        <p role="status" className="rounded-lg bg-primary/10 p-4">
          {notice}
        </p>
      )}
    </section>
  )
}
