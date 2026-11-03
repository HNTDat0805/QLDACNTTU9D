import { useMutation, useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  AlertCircle,
  CalendarClock,
  CheckCircle2,
  MapPin,
  ShieldCheck,
  Smartphone,
  UserCheck,
  Wrench,
} from "lucide-react"
import { type ReactNode, useEffect, useRef, useState } from "react"
import { AppointmentsService, ServicesService, SlotsService } from "@/client"
import { PublicLayout } from "@/components/Common/PublicLayout"
import { money } from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { pageHead } from "@/lib/seo"
import { formatLocalDate, getApiErrorMessage } from "@/utils"

export const Route = createFileRoute("/booking")({
  component: BookingPage,
  head: pageHead("Đặt lịch sửa chữa"),
})

const popularBrands = ["Apple", "Samsung", "Oppo", "Xiaomi", "Khác"]

const bookingSteps = [
  { step: 1, title: "1. Chọn dịch vụ" },
  { step: 2, title: "2. Thiết bị & liên hệ" },
  { step: 3, title: "3. Ngày & khung giờ" },
  { step: 4, title: "4. Xác nhận" },
]

function BookingPage() {
  const { user: currentUser } = useAuth()
  const [serviceId, setServiceId] = useState(() => {
    if (typeof window === "undefined") return ""
    return new URLSearchParams(window.location.search).get("serviceId") ?? ""
  })
  const [date, setDate] = useState(() => formatLocalDate())
  const [time, setTime] = useState("")
  const [technicianId, setTechnicianId] = useState("")
  const [name, setName] = useState("")
  const [phone, setPhone] = useState("")
  const [brand, setBrand] = useState("")
  const [model, setModel] = useState("")
  const [result, setResult] = useState<string>()
  const [bookedCode, setBookedCode] = useState<string>()
  const [clientError, setClientError] = useState<string | null>(null)
  const isSubmittingRef = useRef(false)

  useEffect(() => {
    const savedService = sessionStorage.getItem("fixphone_booking_service")
    if (savedService) {
      sessionStorage.removeItem("fixphone_booking_service")
      setServiceId((prev) => prev || savedService)
    }
    if (currentUser?.full_name && !name) {
      setName(currentUser.full_name)
    }
  }, [currentUser, name])

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
    onSuccess: ({ data }) => {
      setBookedCode(data.appointment_code)
      setResult(`Đặt lịch thành công. Mã lịch: ${data.appointment_code}`)
    },
    onSettled: () => {
      isSubmittingRef.current = false
    },
  })
  const error =
    services.error || slots.error || technicians.error || booking.error
  const selectedService = services.data?.data.find((s) => s.id === serviceId)
  const selectedTechnician = technicians.data?.find(
    (t) => t.id === technicianId,
  )

  const validateForm = (): boolean => {
    setClientError(null)
    if (!serviceId) {
      setClientError("Vui lòng chọn dịch vụ sửa chữa.")
      document.getElementById("booking-service")?.focus()
      return false
    }
    if (!date) {
      setClientError("Vui lòng chọn ngày hẹn sửa chữa.")
      document.getElementById("booking-date")?.focus()
      return false
    }
    if (!time) {
      setClientError("Vui lòng chọn một khung giờ trống bên trên.")
      return false
    }
    if (!phone.trim()) {
      setClientError(
        "Vui lòng nhập số điện thoại để cửa hàng liên hệ xác nhận.",
      )
      document.getElementById("booking-phone")?.focus()
      return false
    }
    if (phone.trim().length < 8) {
      setClientError("Số điện thoại không hợp lệ (tối thiểu 8 chữ số).")
      document.getElementById("booking-phone")?.focus()
      return false
    }
    return true
  }

  const currentStep = result
    ? 4
    : serviceId && date && time && phone
      ? 4
      : serviceId && (brand || model || phone)
        ? 3
        : serviceId
          ? 2
          : 1

  return (
    <PublicLayout>
      <section
        className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14"
        aria-labelledby="booking-title"
      >
        <div className="max-w-2xl">
          <h1 id="booking-title" className="text-3xl font-bold tracking-tight">
            Đặt lịch sửa chữa
          </h1>
          <p className="mt-2 text-muted-foreground">
            Chọn dịch vụ, thiết bị, ngày và giờ phù hợp. Nhân viên hoặc hệ thống
            sẽ phân công kỹ thuật viên sẵn sàng đón tiếp bạn.
          </p>
        </div>

        {/* 4-Step Progress Indicator (Figma KH03–KH06) */}
        <ol
          aria-label="Các bước đặt lịch sửa chữa"
          className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4"
        >
          {bookingSteps.map(({ step, title }) => {
            const done = currentStep > step || Boolean(result)
            const active = currentStep === step && !result
            return (
              <li
                key={step}
                className={`flex items-center gap-2.5 rounded-xl border px-3.5 py-2.5 text-sm font-medium transition-colors ${
                  done
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                    : active
                      ? "border-primary bg-primary/10 text-primary"
                      : "bg-card text-muted-foreground"
                }`}
              >
                <span
                  className={`grid size-6 shrink-0 place-items-center rounded-full text-xs font-bold ${
                    done
                      ? "bg-emerald-600 text-white"
                      : active
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                  }`}
                >
                  {done ? "✓" : step}
                </span>
                <span className="truncate">{title}</span>
              </li>
            )
          })}
        </ol>

        <div className="mt-8 grid items-start gap-6 lg:grid-cols-[1fr_360px]">
          <Card>
            <CardHeader>
              <CardTitle>Thông tin lịch hẹn</CardTitle>
            </CardHeader>
            <CardContent>
              <form
                noValidate
                className="grid gap-5"
                onSubmit={(event) => {
                  event.preventDefault()
                  if (!validateForm()) return
                  if (isSubmittingRef.current || booking.isPending) return
                  isSubmittingRef.current = true
                  booking.mutate()
                }}
              >
                {/* Step 1: Chọn dịch vụ */}
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

                {/* Quick Service Cards (Figma KH03) */}
                {services.data?.data && services.data.data.length > 0 && (
                  <div className="grid gap-2.5 sm:grid-cols-2">
                    {services.data.data.slice(0, 4).map((service) => {
                      const isSelected = service.id === serviceId
                      return (
                        <button
                          key={service.id}
                          type="button"
                          onClick={() => {
                            setServiceId(service.id)
                            setTime("")
                            setTechnicianId("")
                          }}
                          className={`flex items-start justify-between gap-2 rounded-xl border p-3 text-left text-sm transition-all ${
                            isSelected
                              ? "border-primary bg-primary/10 ring-1 ring-primary"
                              : "bg-background hover:border-primary/40"
                          }`}
                        >
                          <div>
                            <p className="font-semibold">{service.name}</p>
                            <p className="mt-0.5 text-xs text-muted-foreground">
                              Dự kiến {service.estimated_duration_minutes ?? 30}{" "}
                              phút
                            </p>
                          </div>
                          {service.base_price !== undefined && (
                            <span className="shrink-0 text-xs font-semibold text-primary">
                              {money(service.base_price)}
                            </span>
                          )}
                        </button>
                      )
                    })}
                  </div>
                )}

                {services.data?.data.length === 0 && (
                  <p className="rounded-md border p-3 text-sm text-muted-foreground">
                    Cửa hàng chưa có dịch vụ để đặt lịch.
                  </p>
                )}

                {/* Step 3: Ngày & Giờ */}
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Ngày hẹn" htmlFor="booking-date">
                    <Input
                      id="booking-date"
                      type="date"
                      min={formatLocalDate()}
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
                </div>

                <fieldset>
                  <legend className="text-sm font-medium">
                    Khung giờ trống
                  </legend>
                  <div className="mt-2 flex flex-wrap gap-2" aria-live="polite">
                    {!serviceId ? (
                      <p className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
                        💡 Vui lòng chọn dịch vụ ở phía trên để xem các khung
                        giờ trống phù hợp.
                      </p>
                    ) : !date ? (
                      <p className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
                        💡 Vui lòng chọn ngày hẹn để tải danh sách khung giờ.
                      </p>
                    ) : slots.isLoading ? (
                      <span className="text-sm text-muted-foreground">
                        Đang tải khung giờ...
                      </span>
                    ) : slots.data?.available_slots &&
                      slots.data.available_slots.length > 0 ? (
                      slots.data.available_slots.map((slot) => (
                        <Button
                          key={slot.start_time}
                          type="button"
                          variant={
                            time === slot.start_time ? "default" : "outline"
                          }
                          disabled={!slot.available}
                          onClick={() => setTime(slot.start_time)}
                          className={
                            time === slot.start_time
                              ? "ring-2 ring-primary font-bold"
                              : ""
                          }
                        >
                          {slot.start_time}
                        </Button>
                      ))
                    ) : (
                      <span className="text-sm text-muted-foreground">
                        Không còn khung giờ trống.
                      </span>
                    )}
                  </div>
                </fieldset>

                {/* Step 2: Thiết bị & Thông tin khách hàng */}
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Số điện thoại" htmlFor="booking-phone">
                    <Input
                      id="booking-phone"
                      value={phone}
                      onChange={(event) => setPhone(event.target.value)}
                      placeholder="VD: 0901234567"
                      autoComplete="tel"
                      required
                    />
                  </Field>
                  <Field label="Họ tên" htmlFor="booking-name">
                    <Input
                      id="booking-name"
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      placeholder="VD: Nguyễn Văn A"
                    />
                  </Field>
                </div>

                <div className="space-y-2">
                  <span className="text-xs font-medium text-muted-foreground">
                    Chọn nhanh hãng điện thoại:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {popularBrands.map((b) => (
                      <button
                        key={b}
                        type="button"
                        onClick={() => setBrand(b)}
                        className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                          brand === b
                            ? "border-primary bg-primary text-primary-foreground"
                            : "bg-background hover:border-primary/40"
                        }`}
                      >
                        {b}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Hãng điện thoại" htmlFor="booking-brand">
                    <Input
                      id="booking-brand"
                      value={brand}
                      onChange={(event) => setBrand(event.target.value)}
                      placeholder="VD: Apple, Samsung..."
                    />
                  </Field>
                  <Field label="Dòng máy" htmlFor="booking-model">
                    <Input
                      id="booking-model"
                      value={model}
                      onChange={(event) => setModel(event.target.value)}
                      placeholder="VD: iPhone 13 Pro"
                    />
                  </Field>
                </div>

                {error && (
                  <p role="alert" className="text-sm text-destructive">
                    {getApiErrorMessage(error)}
                  </p>
                )}

                {result && (
                  <div
                    role="status"
                    className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-4 text-sm"
                  >
                    <div className="flex items-center gap-2 font-semibold text-emerald-700 dark:text-emerald-300">
                      <CheckCircle2 aria-hidden="true" className="size-5" />
                      <span>{result}</span>
                    </div>
                    {bookedCode && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {isLoggedIn() ? (
                          <Button asChild size="sm" variant="outline">
                            <Link
                              to="/appointments"
                              onClick={() =>
                                sessionStorage.setItem(
                                  "fixphone_lookup",
                                  bookedCode,
                                )
                              }
                            >
                              Xem đơn của tôi
                            </Link>
                          </Button>
                        ) : (
                          <Button asChild size="sm" variant="outline">
                            <Link
                              to="/login"
                              onClick={() =>
                                sessionStorage.setItem(
                                  "fixphone_lookup",
                                  bookedCode,
                                )
                              }
                            >
                              Đăng nhập để theo dõi đơn
                            </Link>
                          </Button>
                        )}
                        <Button asChild size="sm" variant="ghost">
                          <Link to="/">Về trang chủ</Link>
                        </Button>
                      </div>
                    )}
                  </div>
                )}

                <div className="space-y-3 pt-2">
                  {clientError && (
                    <div
                      data-testid="booking-validation-error"
                      className="flex items-center gap-2 rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive font-medium"
                    >
                      <AlertCircle
                        aria-hidden="true"
                        className="size-4 shrink-0"
                      />
                      <span>{clientError}</span>
                    </div>
                  )}

                  {!serviceId || !date || !time || !phone.trim() ? (
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span>Cần hoàn tất:</span>
                      {!serviceId && (
                        <span className="rounded-md bg-amber-500/10 px-2 py-0.5 font-medium text-amber-700 dark:text-amber-300">
                          1. Chọn dịch vụ
                        </span>
                      )}
                      {!date && (
                        <span className="rounded-md bg-amber-500/10 px-2 py-0.5 font-medium text-amber-700 dark:text-amber-300">
                          2. Chọn ngày
                        </span>
                      )}
                      {!time && (
                        <span className="rounded-md bg-amber-500/10 px-2 py-0.5 font-medium text-amber-700 dark:text-amber-300">
                          3. Chọn khung giờ
                        </span>
                      )}
                      {!phone.trim() && (
                        <span className="rounded-md bg-amber-500/10 px-2 py-0.5 font-medium text-amber-700 dark:text-amber-300">
                          4. Số điện thoại
                        </span>
                      )}
                    </div>
                  ) : null}

                  <Button
                    type="submit"
                    size="lg"
                    className="w-full sm:w-auto font-semibold btn-primary-glow cursor-pointer"
                    disabled={booking.isPending}
                  >
                    {booking.isPending
                      ? "Đang xác nhận đặt lịch..."
                      : "Xác nhận đặt lịch"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Right Summary Card (Figma KH06 Tóm tắt lịch hẹn) */}
          <Card className="lg:sticky lg:top-24">
            <CardHeader>
              <CardTitle className="text-base">Tóm tắt lịch hẹn</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="flex items-start gap-3">
                <Wrench
                  aria-hidden="true"
                  className="mt-0.5 size-4 shrink-0 text-primary"
                />
                <div>
                  <p className="text-xs text-muted-foreground">Dịch vụ</p>
                  <p className="font-medium">
                    {selectedService
                      ? `${selectedService.name} (${selectedService.estimated_duration_minutes ?? 30} phút)`
                      : "Chưa chọn dịch vụ"}
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Smartphone
                  aria-hidden="true"
                  className="mt-0.5 size-4 shrink-0 text-primary"
                />
                <div>
                  <p className="text-xs text-muted-foreground">Thiết bị</p>
                  <p className="font-medium">
                    {[brand, model].filter(Boolean).join(" ") ||
                      "Chưa nhập thông tin máy"}
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <CalendarClock
                  aria-hidden="true"
                  className="mt-0.5 size-4 shrink-0 text-primary"
                />
                <div>
                  <p className="text-xs text-muted-foreground">Thời gian hẹn</p>
                  <p className="font-medium">
                    {date && time
                      ? `${time} — ${date}`
                      : date
                        ? `${date} (chưa chọn giờ)`
                        : "Chưa chọn ngày & giờ"}
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <UserCheck
                  aria-hidden="true"
                  className="mt-0.5 size-4 shrink-0 text-primary"
                />
                <div>
                  <p className="text-xs text-muted-foreground">Kỹ thuật viên</p>
                  <p className="font-medium">
                    {selectedTechnician?.full_name ||
                      "Hệ thống tự phân công kỹ thuật viên"}
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <MapPin
                  aria-hidden="true"
                  className="mt-0.5 size-4 shrink-0 text-primary"
                />
                <div>
                  <p className="text-xs text-muted-foreground">Địa điểm</p>
                  <p className="font-medium">Cửa hàng FixPhone</p>
                </div>
              </div>

              <div className="border-t pt-4">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Tạm tính</span>
                  <span className="text-lg font-bold text-primary">
                    {selectedService?.base_price !== undefined
                      ? money(selectedService.base_price)
                      : "Báo giá sau kiểm tra"}
                  </span>
                </div>
                <p className="mt-2 flex items-center gap-1.5 text-xs text-emerald-700 dark:text-emerald-300">
                  <ShieldCheck aria-hidden="true" className="size-4 shrink-0" />
                  Bảo hành 6 tháng · Kiểm tra máy miễn phí
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
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
