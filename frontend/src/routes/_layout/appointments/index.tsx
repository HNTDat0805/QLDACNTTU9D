import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { useEffect, useState } from "react"
import { AppointmentsService } from "@/client"
import {
  dateTime,
  Pager,
  PageTitle,
  Status,
} from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { pageHead } from "@/lib/seo"
import { getApiErrorMessage } from "@/utils"

export const Route = createFileRoute("/_layout/appointments/")({
  component: MyAppointments,
  head: pageHead("Lịch hẹn của tôi"),
})

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

function MyAppointments() {
  const [page, setPage] = useState(0)
  const [statusFilter, setStatusFilter] = useState<
    "ALL" | "ACTIVE" | "COMPLETED" | "CANCELLED"
  >("ALL")
  const [lookupInput, setLookupInput] = useState("")
  const [lookupKeyword, setLookupKeyword] = useState("")

  useEffect(() => {
    const saved = sessionStorage.getItem("fixphone_lookup")
    if (saved) {
      sessionStorage.removeItem("fixphone_lookup")
      setLookupInput(saved)
      setLookupKeyword(saved)
    }
  }, [])

  const appointments = useQuery({
    queryKey: ["my-appointments", page],
    queryFn: async () =>
      (
        await AppointmentsService.readMyAppointments({
          query: { skip: page * 20, limit: 20 },
        })
      ).data,
  })

  const lookup = useQuery({
    queryKey: ["appointment-lookup", lookupKeyword],
    enabled: Boolean(lookupKeyword),
    queryFn: async () => {
      const isPhone = /^[0-9+\s-]{8,15}$/.test(lookupKeyword)
      return (
        await AppointmentsService.lookupAppointment({
          query: isPhone
            ? { phone_number: lookupKeyword }
            : { appointment_number: lookupKeyword },
        })
      ).data
    },
  })

  if (appointments.isLoading) return <p>Đang tải lịch hẹn...</p>
  if (appointments.error)
    return <p role="alert">{getApiErrorMessage(appointments.error)}</p>

  const allItems = appointments.data?.data ?? []
  const filteredItems = allItems.filter((item) => {
    if (statusFilter === "ALL") return true
    if (statusFilter === "COMPLETED") return item.status === "COMPLETED"
    if (statusFilter === "CANCELLED")
      return item.status === "CANCELLED" || item.status === "NO_SHOW"
    return !["COMPLETED", "CANCELLED", "NO_SHOW"].includes(item.status)
  })

  return (
    <section className="space-y-6">
      <PageTitle
        title="Lịch hẹn của tôi"
        description="Xem thời gian, tiến độ sửa chữa 4 bước và các thao tác được phép cho lịch hẹn."
      >
        <Button asChild>
          <Link to="/booking">Đặt lịch mới</Link>
        </Button>
      </PageTitle>

      {/* Quick Order Lookup Card (Figma KH08 Tra cứu đơn) */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            Tra cứu tiến độ sửa chữa nhanh
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <form
            className="flex flex-col gap-2 sm:flex-row"
            onSubmit={(event) => {
              event.preventDefault()
              setLookupKeyword(lookupInput.trim())
            }}
          >
            <div className="relative flex-1">
              <Search
                aria-hidden="true"
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
              />
              <Input
                value={lookupInput}
                onChange={(event) => setLookupInput(event.target.value)}
                placeholder="Nhập mã lịch hẹn (VD: APPT-...) hoặc số điện thoại"
                aria-label="Tra cứu theo mã lịch hẹn hoặc số điện thoại"
                className="pl-9"
              />
            </div>
            <Button type="submit" disabled={!lookupInput.trim()}>
              Tra cứu
            </Button>
            {lookupKeyword && (
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  setLookupInput("")
                  setLookupKeyword("")
                }}
              >
                Xóa bộ lọc
              </Button>
            )}
          </form>

          {lookupKeyword && lookup.isLoading && (
            <p className="text-sm text-muted-foreground">
              Đang tra cứu đơn {lookupKeyword}...
            </p>
          )}
          {lookupKeyword && lookup.error && (
            <p role="alert" className="text-sm text-destructive">
              {getApiErrorMessage(lookup.error)}
            </p>
          )}
          {lookupKeyword && lookup.data && lookup.data.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Không tìm thấy lịch hẹn phù hợp với &ldquo;{lookupKeyword}&rdquo;.
            </p>
          )}
          {lookupKeyword && lookup.data && lookup.data.length > 0 && (
            <div className="space-y-3 border-t pt-3">
              {lookup.data.map((found) => (
                <div
                  key={found.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/30 p-3 text-sm"
                >
                  <div>
                    <p className="font-semibold">{found.appointment_number}</p>
                    <p className="text-xs text-muted-foreground">
                      {dateTime(found.appointment_date)} ·{" "}
                      {found.services?.map((s) => s.service_name).join(", ")}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Status value={found.status} />
                    <Button asChild size="sm" variant="outline">
                      <Link
                        to="/appointments/$appointmentId"
                        params={{ appointmentId: found.id }}
                      >
                        Xem chi tiết
                      </Link>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Filter Tabs (Figma KH09) */}
      <div className="flex flex-wrap gap-2">
        {[
          { key: "ALL", label: "Tất cả" },
          { key: "ACTIVE", label: "Đang xử lý" },
          { key: "COMPLETED", label: "Hoàn tất" },
          { key: "CANCELLED", label: "Đã hủy" },
        ].map((tab) => (
          <Button
            key={tab.key}
            type="button"
            size="sm"
            variant={statusFilter === tab.key ? "default" : "outline"}
            onClick={() => {
              setStatusFilter(
                tab.key as "ALL" | "ACTIVE" | "COMPLETED" | "CANCELLED",
              )
              setPage(0)
            }}
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {filteredItems.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            Bạn chưa có lịch hẹn nào.
          </CardContent>
        </Card>
      ) : (
        filteredItems.map((appointment) => {
          const activeStep = getStepIndex(appointment.status)
          return (
            <Card key={appointment.id}>
              <CardContent className="space-y-4 py-5">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <p className="font-semibold">
                      {appointment.appointment_number}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {dateTime(appointment.appointment_date)}
                    </p>
                    <p className="mt-1 text-sm">
                      {appointment.services
                        ?.map((s) => s.service_name)
                        .join(", ")}
                    </p>
                    {appointment.device && (
                      <p className="text-xs text-muted-foreground">
                        Thiết bị: {appointment.device.brand}{" "}
                        {appointment.device.model}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <Status value={appointment.status} />
                    <Button asChild variant="outline">
                      <Link
                        to="/appointments/$appointmentId"
                        params={{ appointmentId: appointment.id }}
                      >
                        Xem chi tiết
                      </Link>
                    </Button>
                  </div>
                </div>

                {/* 4-Step Progress Tracker (Figma KH08) */}
                {activeStep >= 0 && (
                  <ol
                    aria-label="Tiến độ sửa chữa"
                    className="grid grid-cols-4 gap-2 border-t pt-3 text-xs"
                  >
                    {progressSteps.map((step, index) => {
                      const reached = index <= activeStep
                      return (
                        <li
                          key={step.key}
                          className={`flex items-center gap-1.5 font-medium ${
                            reached ? "text-primary" : "text-muted-foreground"
                          }`}
                        >
                          <span
                            className={`inline-block size-2 rounded-full ${
                              reached ? "bg-primary" : "bg-muted-foreground/30"
                            }`}
                          />
                          <span>{step.label}</span>
                        </li>
                      )
                    })}
                  </ol>
                )}
              </CardContent>
            </Card>
          )
        })
      )}
      <Pager
        page={page}
        count={appointments.data?.count ?? 0}
        setPage={setPage}
      />
    </section>
  )
}
