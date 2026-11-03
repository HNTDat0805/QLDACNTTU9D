import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  AlertCircle,
  Calendar,
  CheckCircle2,
  Clock,
  XCircle,
} from "lucide-react"
import { useState } from "react"
import { AppointmentsService, SlotsService } from "@/client"
import { dateTime, Status } from "@/components/Operations/shared"
import { Badge } from "@/components/ui/badge"
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
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { pageHead } from "@/lib/seo"
import { cn } from "@/lib/utils"
import { formatLocalDate, getApiErrorMessage } from "@/utils"

export const Route = createFileRoute("/_layout/appointments/$appointmentId")({
  component: AppointmentDetail,
  head: pageHead("Chi tiết lịch hẹn"),
})

const mutableStatuses = new Set(["PENDING", "CONFIRMED"])

const progressSteps = [
  { key: "PENDING", label: "Mới" },
  { key: "CONFIRMED", label: "Xác nhận" },
  { key: "IN_PROGRESS", label: "Đang sửa" },
  { key: "COMPLETED", label: "Hoàn tất" },
]

function getStepIndex(status: string): number {
  switch (status) {
    case "PENDING":
      return 0
    case "CONFIRMED":
      return 1
    case "ARRIVED":
    case "IN_PROGRESS":
    case "WAITING_PARTS":
    case "READY":
      return 2
    case "COMPLETED":
      return 3
    default:
      return -1
  }
}

function AppointmentDetail() {
  const { appointmentId } = Route.useParams()
  const { user } = useAuth()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const queryClient = useQueryClient()
  const [reason, setReason] = useState("")
  const [dialogReason, setDialogReason] = useState("")
  const [date, setDate] = useState("")
  const [time, setTime] = useState("")
  const [notice, setNotice] = useState("")
  const [validationError, setValidationError] = useState<string | null>(null)
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
  const technicianId = detail.data?.technician?.id
  const slots = useQuery({
    queryKey: ["reschedule-slots", serviceId, date, technicianId],
    enabled: Boolean(serviceId && date),
    queryFn: async () =>
      (
        await SlotsService.getAvailableSlots({
          query: {
            service_id: serviceId ?? "",
            date,
            technician_id: technicianId ?? undefined,
          },
        })
      ).data,
  })
  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["my-appointments"] })
    queryClient.invalidateQueries({ queryKey: ["operations"] })
    queryClient.invalidateQueries({ queryKey: ["reschedule-slots"] })
  }
  const cancel = useMutation({
    mutationFn: (customReason?: string) => {
      const cancelReason = (customReason || dialogReason || reason).trim()
      return AppointmentsService.cancelAppointment({
        path: { appointment_id: appointmentId },
        body: { reason: cancelReason },
      })
    },
    onSuccess: () => {
      setNotice("Đã hủy lịch thành công")
      showSuccessToast("Đã hủy lịch hẹn thành công.")
      setCancelOpen(false)
      setValidationError(null)
      invalidate()
      detail.refetch()
    },
    onError: (err) => {
      showErrorToast(getApiErrorMessage(err))
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
      showSuccessToast(`Đã đổi lịch sang ngày ${date} lúc ${time} thành công!`)
      setValidationError(null)
      invalidate()
      detail.refetch()
    },
    onError: (err) => {
      showErrorToast(getApiErrorMessage(err))
    },
  })

  const isStaff =
    Boolean(user?.is_superuser) ||
    ["admin", "manager", "staff", "technician"].includes(user?.role ?? "")

  const confirmMutation = useMutation({
    mutationFn: async () => {
      // 1. Nếu đã chọn ngày + giờ mới: Xác nhận đổi sang ngày giờ mới
      if (date && time) {
        return (
          await AppointmentsService.updateAppointment({
            path: { appointment_id: appointmentId },
            body: {
              appointment_date: date,
              start_time: time,
              reschedule_reason: reason || undefined,
            },
          })
        ).data
      }

      // 2. Nếu nhân viên / quản lý / kỹ thuật viên: Gọi API confirm đổi trạng thái sang CONFIRMED
      if (isStaff) {
        return (
          await AppointmentsService.confirmAppointment({
            path: { appointment_id: appointmentId },
          })
        ).data
      }

      // 3. Nếu khách hàng: Ghi nhận xác nhận thông tin lịch hẹn
      return (
        await AppointmentsService.updateAppointment({
          path: { appointment_id: appointmentId },
          body: {
            reschedule_reason: reason || "Khách hàng xác nhận lịch hẹn",
          },
        })
      ).data
    },
    onSuccess: () => {
      const msg =
        date && time
          ? `Đã xác nhận đổi lịch sang ngày ${date} lúc ${time} thành công!`
          : "Đã xác nhận lịch hẹn thành công!"
      setNotice(msg)
      showSuccessToast(msg)
      setValidationError(null)
      invalidate()
      detail.refetch()
    },
    onError: (err) => {
      showErrorToast(getApiErrorMessage(err))
    },
  })

  const handleConfirmClick = () => {
    setValidationError(null)
    if (date && !time) {
      const msg =
        "Vui lòng chọn một khung giờ trống khả dụng trước khi bấm xác nhận."
      setValidationError(msg)
      showErrorToast(msg)
      return
    }
    confirmMutation.mutate()
  }

  const handleRescheduleClick = () => {
    setValidationError(null)
    if (!date) {
      const msg = "Vui lòng chọn ngày mới trước khi bấm đổi lịch."
      setValidationError(msg)
      showErrorToast(msg)
      const dateEl = document.getElementById("reschedule-date")
      dateEl?.focus()
      return
    }
    if (!time) {
      const msg = "Vui lòng chọn một khung giờ trống khả dụng."
      setValidationError(msg)
      showErrorToast(msg)
      return
    }
    reschedule.mutate()
  }

  const handleOpenCancelDialog = () => {
    setValidationError(null)
    setDialogReason(reason.trim())
    setCancelOpen(true)
  }

  const handleConfirmCancel = () => {
    const finalReason = (dialogReason || reason).trim()
    if (!finalReason) {
      setValidationError("Vui lòng nhập hoặc chọn lý do hủy lịch.")
      showErrorToast("Vui lòng nhập hoặc chọn lý do hủy lịch.")
      return
    }
    cancel.mutate(finalReason)
  }

  const quickReasons = [
    "Bận việc đột xuất",
    "Đã tự khắc phục được máy",
    "Muốn dời sang tuần sau",
    "Đổi ý không sửa nữa",
  ]
  if (detail.isLoading)
    return <p className="text-muted-foreground">Đang tải lịch hẹn...</p>
  if (detail.error || !detail.data)
    return (
      <p role="alert" className="text-destructive">
        {getApiErrorMessage(detail.error)}
      </p>
    )
  const canChange = mutableStatuses.has(detail.data.status)
  const isConfirmed = detail.data.status === "CONFIRMED"
  const error = cancel.error || reschedule.error || slots.error
  const activeStep = getStepIndex(detail.data.status)

  return (
    <section className="space-y-6" aria-labelledby="appointment-title">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button asChild variant="ghost">
          <Link to="/appointments">← Lịch hẹn của tôi</Link>
        </Button>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline" size="sm">
            <Link to="/quotes">Xem báo giá</Link>
          </Button>
          {user?.role !== "technician" && (
            <Button asChild variant="outline" size="sm">
              <Link to="/invoices">Xem hóa đơn</Link>
            </Button>
          )}
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
          <CardTitle id="appointment-title">
            {detail.data.appointment_number}
          </CardTitle>
          <Status value={detail.data.status} />
        </CardHeader>
        <CardContent className="space-y-4">
          {activeStep >= 0 && (
            <ol
              aria-label="Tiến độ xử lý đơn"
              className="grid grid-cols-2 gap-2 rounded-xl border bg-muted/30 p-3 text-xs sm:grid-cols-4"
            >
              {progressSteps.map((step, index) => {
                const reached = index <= activeStep
                return (
                  <li
                    key={step.key}
                    className={`flex items-center gap-2 font-semibold ${
                      reached ? "text-primary" : "text-muted-foreground"
                    }`}
                  >
                    <span
                      className={`grid size-5 shrink-0 place-items-center rounded-full text-[11px] ${
                        reached
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {reached ? "✓" : index + 1}
                    </span>
                    <span>{step.label}</span>
                  </li>
                )
              })}
            </ol>
          )}

          <div className="grid gap-2 text-sm sm:grid-cols-2">
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
            {detail.data.technician && (
              <p>
                <strong>Kỹ thuật viên:</strong>{" "}
                {detail.data.technician.full_name}
              </p>
            )}
          </div>

          {detail.data.status_history &&
            detail.data.status_history.length > 0 && (
              <div className="border-t pt-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Nhật ký cập nhật trạng thái
                </p>
                <ul className="space-y-2 text-xs">
                  {detail.data.status_history.map((entry) => (
                    <li
                      key={entry.id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-muted/40 px-3 py-2"
                    >
                      <span>
                        <strong>{entry.new_status}</strong>
                        {entry.note ? ` — ${entry.note}` : ""}
                      </span>
                      <span className="text-muted-foreground">
                        {dateTime(entry.created_at)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
        </CardContent>
      </Card>
      {canChange && (
        <Card className="border-border/80 shadow-xs">
          <CardHeader>
            <CardTitle className="text-lg">Đổi hoặc hủy lịch</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-5">
            {/* Ngày mới */}
            <div className="grid gap-2">
              <Label
                htmlFor="reschedule-date"
                className="text-sm font-semibold flex items-center gap-1.5"
              >
                <Calendar className="size-4 text-primary" />
                Ngày mới
              </Label>
              <Input
                id="reschedule-date"
                type="date"
                min={formatLocalDate()}
                value={date}
                onChange={(event) => {
                  setDate(event.target.value)
                  setTime("")
                  setValidationError(null)
                }}
                className="max-w-xs"
              />
              {!date && (
                <p className="text-xs text-muted-foreground">
                  💡 Vui lòng chọn ngày để hiển thị các khung giờ trống khả
                  dụng.
                </p>
              )}
            </div>

            {/* Khung giờ trống */}
            {date && (
              <div className="grid gap-2 rounded-xl border border-border/70 bg-muted/20 p-3.5">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-semibold flex items-center gap-1.5 text-foreground">
                    <Clock className="size-3.5 text-primary" />
                    Khung giờ trống cho ngày {date}
                  </Label>
                  {time && (
                    <Badge
                      variant="outline"
                      className="text-primary border-primary/30 bg-primary/5 text-xs"
                    >
                      Đã chọn: {time}
                    </Badge>
                  )}
                </div>

                {slots.isLoading ? (
                  <p className="text-xs text-muted-foreground animate-pulse py-2">
                    Đang tải danh sách khung giờ trống...
                  </p>
                ) : slots.isError ? (
                  <p className="text-xs text-destructive py-2">
                    Không thể tải khung giờ. Vui lòng thử lại.
                  </p>
                ) : slots.data?.available_slots &&
                  slots.data.available_slots.length > 0 ? (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {slots.data.available_slots.map((slot) => (
                      <Button
                        key={slot.start_time}
                        type="button"
                        size="sm"
                        variant={
                          time === slot.start_time ? "default" : "outline"
                        }
                        disabled={!slot.available}
                        onClick={() => {
                          setTime(slot.start_time)
                          setValidationError(null)
                        }}
                        className={cn(
                          "font-medium transition-all text-xs h-8 px-3 cursor-pointer",
                          time === slot.start_time &&
                            "ring-2 ring-primary ring-offset-1 font-semibold",
                        )}
                      >
                        {slot.start_time}
                      </Button>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-amber-600 font-medium py-1">
                    Không còn khung giờ trống trong ngày này. Vui lòng chọn ngày
                    khác.
                  </p>
                )}
              </div>
            )}

            {/* Lý do thay đổi hoặc hủy */}
            <div className="grid gap-2">
              <Label
                htmlFor="appointment-reason"
                className="text-sm font-semibold"
              >
                Lý do thay đổi hoặc hủy
              </Label>
              <Input
                id="appointment-reason"
                placeholder="Ghi chú lý do nếu cần..."
                value={reason}
                onChange={(event) => {
                  setReason(event.target.value)
                  if (validationError) setValidationError(null)
                }}
              />
              <p className="text-xs text-muted-foreground">
                Ghi chú lý do giúp nhân viên và kỹ thuật viên nắm rõ nhu cầu của
                bạn.
              </p>
            </div>

            {/* Validation alert nếu bấm nút khi chưa điền thông tin */}
            {validationError && (
              <p
                role="alert"
                className="text-xs text-destructive font-medium flex items-center gap-1.5"
              >
                <AlertCircle className="size-4 shrink-0" />
                {validationError}
              </p>
            )}

            {/* Ba nút hành động: luôn bấm được, không disabled cứng */}
            <div className="flex flex-wrap gap-3 pt-1">
              <Button
                type="button"
                disabled={
                  confirmMutation.isPending ||
                  reschedule.isPending ||
                  cancel.isPending
                }
                onClick={handleConfirmClick}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium cursor-pointer shadow-xs"
              >
                <CheckCircle2 className="size-4 mr-1.5 shrink-0" />
                {confirmMutation.isPending
                  ? "Đang xác nhận..."
                  : isConfirmed && !date
                    ? "Đã xác nhận"
                    : "Xác nhận"}
              </Button>
              <Button
                type="button"
                disabled={
                  reschedule.isPending ||
                  cancel.isPending ||
                  confirmMutation.isPending
                }
                onClick={handleRescheduleClick}
                className="btn-primary-glow font-medium cursor-pointer"
              >
                <Calendar className="size-4 mr-1.5 shrink-0" />
                {reschedule.isPending ? "Đang đổi lịch..." : "Đổi lịch"}
              </Button>
              <Button
                type="button"
                variant="destructive"
                disabled={
                  cancel.isPending ||
                  reschedule.isPending ||
                  confirmMutation.isPending
                }
                onClick={handleOpenCancelDialog}
                className="cursor-pointer"
              >
                <XCircle className="size-4 mr-1.5 shrink-0" />
                {cancel.isPending ? "Đang xử lý..." : "Hủy lịch"}
              </Button>
            </div>

            {/* Hộp thoại xác nhận hủy lịch */}
            <Dialog
              open={cancelOpen}
              onOpenChange={(open) => {
                setCancelOpen(open)
                if (!open) setValidationError(null)
              }}
            >
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2 text-destructive">
                    <XCircle className="size-5" />
                    Xác nhận hủy lịch?
                  </DialogTitle>
                </DialogHeader>
                <div className="space-y-3 py-2 text-sm">
                  <p className="text-muted-foreground">
                    Bạn có chắc chắn muốn hủy lịch hẹn{" "}
                    <strong className="text-foreground font-semibold">
                      {detail.data.appointment_number}
                    </strong>
                    ?
                  </p>

                  <div className="space-y-1.5">
                    <Label
                      htmlFor="cancel-dialog-reason"
                      className="text-xs font-semibold"
                    >
                      Lý do hủy lịch <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="cancel-dialog-reason"
                      placeholder="Nhập lý do hủy lịch..."
                      value={dialogReason}
                      onChange={(e) => {
                        setDialogReason(e.target.value)
                        setReason(e.target.value)
                        if (validationError) setValidationError(null)
                      }}
                    />
                  </div>

                  <div>
                    <span className="text-xs text-muted-foreground block mb-1.5 font-medium">
                      Gợi ý chọn nhanh:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {quickReasons.map((q) => (
                        <button
                          key={q}
                          type="button"
                          onClick={() => {
                            setDialogReason(q)
                            setReason(q)
                            if (validationError) setValidationError(null)
                          }}
                          className={cn(
                            "text-xs px-2.5 py-1 rounded-full border transition-all cursor-pointer",
                            (dialogReason || reason) === q
                              ? "bg-primary/10 border-primary text-primary font-semibold"
                              : "border-border hover:bg-muted text-muted-foreground",
                          )}
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>

                  {validationError && (
                    <p
                      role="alert"
                      className="text-xs text-destructive font-medium flex items-center gap-1"
                    >
                      <AlertCircle className="size-3.5" />
                      {validationError}
                    </p>
                  )}
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setCancelOpen(false)}
                    disabled={cancel.isPending}
                    className="cursor-pointer"
                  >
                    Giữ lại lịch
                  </Button>
                  <Button
                    type="button"
                    variant="destructive"
                    disabled={cancel.isPending}
                    onClick={handleConfirmCancel}
                    className="cursor-pointer"
                  >
                    {cancel.isPending ? "Đang hủy..." : "Xác nhận hủy"}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>

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
