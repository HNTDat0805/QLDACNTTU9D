import { useMutation, useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { type ReactNode, useRef, useState } from "react"

import { AppointmentsService, ServicesService, SlotsService } from "@/client"
import { PublicLayout } from "@/components/Common/PublicLayout"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { getApiErrorMessage } from "@/utils"

export const Route = createFileRoute("/booking")({ component: BookingPage })

function BookingPage() {
  const [serviceId, setServiceId] = useState("")
  const [date, setDate] = useState("")
  const [time, setTime] = useState("")
  const [technicianId, setTechnicianId] = useState("")
  const [name, setName] = useState("")
  const [phone, setPhone] = useState("")
  const [brand, setBrand] = useState("")
  const [model, setModel] = useState("")
  const [result, setResult] = useState<string>()
  const isSubmittingRef = useRef(false)

  const services = useQuery({
    queryKey: ["services"],
    queryFn: async () => (await ServicesService.readPublicServices()).data,
  })
  const slots = useQuery({
    queryKey: ["slots", serviceId, date, technicianId],
    enabled: Boolean(serviceId && date),
    queryFn: async () =>
      (
        await SlotsService.getAvailableSlots({
          query: {
            date,
            service_id: serviceId,
            technician_id: technicianId || undefined,
          },
        })
      ).data,
  })
  const technicians = useQuery({
    queryKey: ["booking-technicians", serviceId, date],
    enabled: Boolean(serviceId && date),
    queryFn: async () =>
      (
        await SlotsService.readBookingTechnicians({
          query: { service_id: serviceId, slot_date: date },
        })
      ).data,
  })
  const booking = useMutation({
    mutationFn: () =>
      AppointmentsService.createAppointment({
        body: {
          customer_name: name || undefined,
          customer_phone: phone,
          service_id: serviceId,
          device_brand: brand || undefined,
          device_model: model || undefined,
          appointment_date: date,
          start_time: time,
          technician_id: technicianId || undefined,
        },
      }),
    onSuccess: ({ data }) =>
      setResult(`Đặt lịch thành công. Mã lịch: ${data.appointment_code}`),
    onSettled: () => {
      isSubmittingRef.current = false
    },
  })
  const error = services.error || slots.error || booking.error

  return (
    <PublicLayout>
      <section
        className="mx-auto max-w-3xl px-4 py-10 sm:py-16"
        aria-labelledby="booking-title"
      >
        <h1 id="booking-title" className="text-3xl font-bold tracking-tight">
          Đặt lịch sửa chữa
        </h1>
        <p className="mt-2 text-muted-foreground">
          Chọn dịch vụ, ngày và giờ phù hợp. Nhân viên sẽ phân công kỹ thuật
          viên.
        </p>
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Thông tin lịch hẹn</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              className="grid gap-5"
              onSubmit={(event) => {
                event.preventDefault()
                if (isSubmittingRef.current) return
                isSubmittingRef.current = true
                booking.mutate()
              }}
            >
              <Field label="Dịch vụ" htmlFor="booking-service">
                <select
                  id="booking-service"
                  className="h-10 w-full rounded-md border bg-background px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={serviceId}
                  onChange={(event) => {
                    setServiceId(event.target.value)
                    setTime("")
                    setTechnicianId("")
                  }}
                  required
                >
                  <option value="">
                    {services.isLoading
                      ? "Đang tải dịch vụ..."
                      : "Chọn dịch vụ"}
                  </option>
                  {services.data?.data.map((service) => (
                    <option key={service.id} value={service.id}>
                      {service.name} ·{" "}
                      {service.estimated_duration_minutes ?? 30} phút
                    </option>
                  ))}
                </select>
              </Field>
              {services.data?.data.length === 0 && (
                <p className="rounded-md border p-3 text-sm text-muted-foreground">
                  Cửa hàng chưa có dịch vụ để đặt lịch.
                </p>
              )}
              <Field label="Ngày hẹn" htmlFor="booking-date">
                <Input
                  id="booking-date"
                  type="date"
                  min={new Date().toISOString().slice(0, 10)}
                  value={date}
                  onChange={(event) => {
                    setDate(event.target.value)
                    setTime("")
                    setTechnicianId("")
                  }}
                  required
                />
              </Field>
              <Field
                label="Kỹ thuật viên (tùy chọn)"
                htmlFor="booking-technician"
              >
                <select
                  id="booking-technician"
                  className="h-10 w-full rounded-md border bg-background px-3"
                  value={technicianId}
                  onChange={(event) => {
                    setTechnicianId(event.target.value)
                    setTime("")
                  }}
                >
                  <option value="">Hệ thống tự phân công</option>
                  {technicians.data?.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.full_name}
                      {t.specialization ? ` · ${t.specialization}` : ""}
                    </option>
                  ))}
                </select>
              </Field>
              <fieldset>
                <legend className="text-sm font-medium">Khung giờ trống</legend>
                <div className="mt-2 flex flex-wrap gap-2" aria-live="polite">
                  {slots.isLoading && (
                    <span className="text-sm text-muted-foreground">
                      Đang tải khung giờ...
                    </span>
                  )}
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
                  {slots.data?.available_slots.length === 0 && (
                    <span className="text-sm text-muted-foreground">
                      Không còn khung giờ trống.
                    </span>
                  )}
                </div>
              </fieldset>
              <Field label="Số điện thoại" htmlFor="booking-phone">
                <Input
                  id="booking-phone"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                  autoComplete="tel"
                  required
                />
              </Field>
              <Field label="Họ tên" htmlFor="booking-name">
                <Input
                  id="booking-name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </Field>
              <Field label="Hãng điện thoại" htmlFor="booking-brand">
                <Input
                  id="booking-brand"
                  value={brand}
                  onChange={(event) => setBrand(event.target.value)}
                />
              </Field>
              <Field label="Dòng máy" htmlFor="booking-model">
                <Input
                  id="booking-model"
                  value={model}
                  onChange={(event) => setModel(event.target.value)}
                />
              </Field>
              {error && (
                <p role="alert" className="text-sm text-destructive">
                  {getApiErrorMessage(error)}
                </p>
              )}
              {result && (
                <p
                  role="status"
                  className="rounded-md bg-primary/10 p-3 text-sm"
                >
                  {result}
                </p>
              )}
              {serviceId && date && time && (
                <div className="rounded-lg border bg-muted/40 p-4 text-sm">
                  <p className="font-medium">Kiểm tra trước khi xác nhận</p>
                  <p>
                    {services.data?.data.find((s) => s.id === serviceId)?.name}{" "}
                    · {date} · {time}
                  </p>
                  <p>
                    {technicians.data?.find((t) => t.id === technicianId)
                      ?.full_name || "Hệ thống tự phân công kỹ thuật viên"}
                  </p>
                </div>
              )}
              <Button
                type="submit"
                disabled={
                  !serviceId || !date || !time || !phone || booking.isPending
                }
              >
                {booking.isPending ? "Đang xác nhận..." : "Xác nhận đặt lịch"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </section>
    </PublicLayout>
  )
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string
  htmlFor: string
  children: ReactNode
}) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
    </div>
  )
}
