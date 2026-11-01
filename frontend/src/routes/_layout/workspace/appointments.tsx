import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import {
  AppointmentsService,
  IntakeService,
  TechniciansService,
} from "@/client"
import {
  ActionForm,
  DataState,
  dateTime,
  money,
  Pager,
  PageTitle,
  Panel,
  Status,
  states,
} from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export const Route = createFileRoute("/_layout/workspace/appointments")({
  component: StaffAppointments,
})
function StaffAppointments() {
  const [q, setQ] = useState("")
  const [status, setStatus] = useState("")
  const [page, setPage] = useState(0)
  const [selected, setSelected] = useState("")
  const list = useQuery({
    queryKey: ["operations", "appointments", q, status, page],
    queryFn: async () =>
      (
        await AppointmentsService.readAppointmentsHistory({
          query: {
            q: q || undefined,
            status: status || undefined,
            skip: page * 20,
            limit: 20,
          },
        })
      ).data,
  })
  const detail = useQuery({
    queryKey: ["operations", "appointment", selected],
    enabled: Boolean(selected),
    queryFn: async () =>
      (
        await AppointmentsService.readAppointmentDetail({
          path: { appointment_id: selected },
        })
      ).data,
  })
  const technicians = useQuery({
    queryKey: ["operations", "technicians", "active"],
    queryFn: async () =>
      (
        await TechniciansService.readTechnicians({
          query: { is_active: true, limit: 100 },
        })
      ).data,
  })
  const appointment = detail.data
  const canChange =
    appointment && ["PENDING", "CONFIRMED"].includes(appointment.status)
  return (
    <section className="space-y-6">
      <PageTitle
        title="Quản lý lịch hẹn"
        description="Tìm lịch, xác nhận và tiếp nhận thiết bị."
      />
      <div className="flex flex-wrap gap-3">
        <Input
          className="max-w-sm"
          aria-label="Tìm lịch hẹn"
          placeholder="Mã lịch, tên hoặc số điện thoại"
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setPage(0)
          }}
        />
        <select
          className="rounded-md border bg-background p-2"
          aria-label="Lọc trạng thái"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value)
            setPage(0)
          }}
        >
          <option value="">Tất cả trạng thái</option>
          {states.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </div>
      <DataState
        pending={list.isPending}
        error={list.error}
        empty={!list.data?.count}
      >
        <div className="grid gap-3">
          {list.data?.data.map((a) => (
            <button
              type="button"
              key={a.id}
              onClick={() => setSelected(a.id)}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card p-4 text-left hover:border-primary focus-visible:ring-2 focus-visible:ring-ring"
            >
              <div>
                <p className="font-semibold">
                  {a.appointment_number} · {a.customer?.full_name}
                </p>
                <p className="text-sm text-muted-foreground">
                  {a.customer?.phone_number} · {dateTime(a.appointment_date)}
                </p>
              </div>
              <Status value={a.status} />
            </button>
          ))}
        </div>
      </DataState>
      <Pager page={page} count={list.data?.count ?? 0} setPage={setPage} />
      {selected && (
        <DataState pending={detail.isPending} error={detail.error}>
          {appointment && (
            <Panel title={`Chi tiết ${appointment.appointment_number}`}>
              <div className="grid gap-6 lg:grid-cols-2">
                <div className="space-y-3">
                  <p>
                    {appointment.customer?.full_name} ·{" "}
                    {appointment.customer?.phone_number}
                  </p>
                  <p>
                    {appointment.device?.brand} {appointment.device?.model}
                  </p>
                  <p>
                    {appointment.services
                      ?.map((s) => s.service_name)
                      .join(", ")}{" "}
                    · {money(appointment.total_amount ?? 0)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {appointment.customer_notes}
                  </p>
                  {appointment.status_history?.map((h) => (
                    <p key={h.id} className="border-l-2 pl-3 text-sm">
                      {dateTime(h.created_at)} · {h.new_status} · {h.note}
                    </p>
                  ))}
                </div>
                <div className="space-y-5">
                  {appointment.status === "PENDING" && (
                    <ActionForm
                      fields={[]}
                      submitLabel="Xác nhận lịch"
                      onSubmit={() =>
                        AppointmentsService.confirmAppointment({
                          path: { appointment_id: selected },
                        })
                      }
                      confirm
                    />
                  )}
                  {canChange && (
                    <>
                      <ActionForm
                        key={`reschedule-${selected}`}
                        fields={[
                          {
                            name: "date",
                            label: "Ngày hẹn mới",
                            type: "date",
                            required: true,
                          },
                          {
                            name: "time",
                            label: "Giờ hẹn mới",
                            type: "time",
                            required: true,
                          },
                          {
                            name: "reason",
                            label: "Lý do đổi lịch",
                            required: true,
                          },
                        ]}
                        submitLabel="Đổi lịch hẹn"
                        confirm
                        onSubmit={(v) =>
                          AppointmentsService.updateAppointment({
                            path: { appointment_id: selected },
                            body: {
                              appointment_date: v.date,
                              start_time: v.time,
                              reschedule_reason: v.reason,
                            },
                          })
                        }
                      />
                      <ActionForm
                        fields={[
                          {
                            name: "reason",
                            label: "Lý do từ chối / hủy",
                            required: true,
                          },
                        ]}
                        submitLabel="Hủy lịch"
                        onSubmit={(v) =>
                          AppointmentsService.cancelAppointment({
                            path: { appointment_id: selected },
                            body: { reason: v.reason },
                          })
                        }
                        confirm
                      />
                      <ActionForm
                        key={`assign-${selected}`}
                        fields={[
                          {
                            name: "technician",
                            label: "Kỹ thuật viên",
                            required: true,
                            options:
                              technicians.data?.data.map((t) => ({
                                value: t.id,
                                label: t.full_name,
                              })) ?? [],
                          },
                        ]}
                        submitLabel="Phân công"
                        onSubmit={(v) =>
                          AppointmentsService.assignTechnicianToAppointment({
                            path: { appointment_id: selected },
                            body: { technician_id: v.technician },
                          })
                        }
                      />
                      <ActionForm
                        key={`intake-${selected}`}
                        fields={[
                          {
                            name: "condition",
                            label: "Ngoại quan thiết bị",
                            required: true,
                          },
                          { name: "fault", label: "Mô tả lỗi", required: true },
                          { name: "accessories", label: "Phụ kiện bàn giao" },
                        ]}
                        submitLabel="Tiếp nhận thiết bị"
                        onSubmit={(v) =>
                          IntakeService.createDeviceIntake({
                            body: {
                              appointment_id: selected,
                              physical_condition: v.condition,
                              fault_description: v.fault,
                              accessories_received: v.accessories || undefined,
                            },
                          })
                        }
                      />
                    </>
                  )}
                </div>
              </div>
            </Panel>
          )}
        </DataState>
      )}
      <Button
        variant="ghost"
        onClick={() => {
          list.refetch()
          if (selected) detail.refetch()
        }}
      >
        Làm mới
      </Button>
    </section>
  )
}
