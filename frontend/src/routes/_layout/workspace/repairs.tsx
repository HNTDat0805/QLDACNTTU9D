import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import {
  DevicesService,
  QuotesService,
  RepairOrdersService,
  TechniciansService,
} from "@/client"
import { QuotesPanel } from "@/components/Operations/QuotesPanel"
import {
  ActionForm,
  DataState,
  dateTime,
  type FieldSpec,
  Pager,
  PageTitle,
  Panel,
  Status,
} from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
export const Route = createFileRoute("/_layout/workspace/repairs")({
  component: Repairs,
})
function Repairs() {
  const { user } = useAuth()
  const reception =
    user?.is_superuser ||
    ["admin", "manager", "staff"].includes(user?.role ?? "")
  const [selected, setSelected] = useState("")
  const [page, setPage] = useState(0)
  const [items, setItems] = useState(1)
  const list = useQuery({
    queryKey: ["operations", "repairs", page],
    queryFn: async () =>
      (
        await RepairOrdersService.ordersReadRepairOrders({
          query: { skip: page * 20, limit: 20 },
        })
      ).data,
  })
  const detail = useQuery({
    queryKey: ["operations", "repair", selected],
    enabled: Boolean(selected),
    queryFn: async () =>
      (
        await RepairOrdersService.ordersReadRepairOrder({
          path: { repair_order_id: selected },
        })
      ).data,
  })
  const techs = useQuery({
    queryKey: ["operations", "technicians", "active"],
    enabled: Boolean(reception),
    queryFn: async () =>
      (
        await TechniciansService.readTechnicians({
          query: { is_active: true, limit: 100 },
        })
      ).data,
  })
  const a = detail.data
  const active = a && !["COMPLETED", "CANCELLED"].includes(a.status)
  const quoteFields: FieldSpec[] = Array.from({ length: items }, (_, i) => [
    { name: `item_${i}`, label: `Hạng mục ${i + 1}`, required: true },
    {
      name: `price_${i}`,
      label: `Đơn giá ${i + 1} (VNĐ)`,
      type: "number" as const,
      min: 0,
      required: true,
    },
    {
      name: `quantity_${i}`,
      label: `Số lượng ${i + 1}`,
      type: "number" as const,
      min: 1,
      required: true,
    },
  ]).flat()
  return (
    <section className="space-y-6">
      <PageTitle
        title={
          user?.role === "technician" && !user.is_superuser
            ? "Công việc được phân công"
            : "Phiếu sửa chữa"
        }
        description="Theo dõi chẩn đoán, báo giá và nhật ký xử lý thiết bị."
      />
      <DataState
        pending={list.isPending}
        error={list.error}
        empty={!list.data?.count}
      >
        <div className="grid gap-3 md:grid-cols-2">
          {list.data?.data.map((row) => (
            <button
              key={row.id}
              type="button"
              className="space-y-2 rounded-xl border bg-card p-4 text-left hover:border-primary"
              onClick={() => {
                setSelected(row.id)
                setItems(1)
              }}
            >
              <p className="font-semibold">
                {row.appointment_number} · {row.customer?.full_name}
              </p>
              <p className="text-sm text-muted-foreground">
                {row.device?.brand} {row.device?.model} ·{" "}
                {dateTime(row.appointment_date)}
              </p>
              <Status value={row.status} />
            </button>
          ))}
        </div>
      </DataState>
      <Pager page={page} count={list.data?.count ?? 0} setPage={setPage} />
      {selected && (
        <DataState pending={detail.isPending} error={detail.error}>
          {a && (
            <>
              <Panel title={`Phiếu ${a.appointment_number}`}>
                <div className="grid gap-6 lg:grid-cols-2">
                  <div className="space-y-3">
                    <p className="font-medium">
                      {a.customer?.full_name} · {a.customer?.phone_number}
                    </p>
                    <p>
                      {a.device?.brand} {a.device?.model}
                    </p>
                    <p>{a.customer_notes}</p>
                    <p>
                      Chẩn đoán: {a.technician_diagnosis || "Chưa có chẩn đoán"}
                    </p>
                    {a.status_history?.map((h) => (
                      <p
                        key={h.id}
                        className="border-l-2 pl-3 text-sm text-muted-foreground"
                      >
                        {dateTime(h.created_at)} · {h.new_status} · {h.note}
                      </p>
                    ))}
                  </div>
                  <div className="space-y-5">
                    {active && (
                      <ActionForm
                        key={`status-${a.id}-${a.status}`}
                        fields={[
                          {
                            name: "status",
                            label: "Trạng thái mới",
                            required: true,
                            options: (a.status === "PENDING"
                              ? ["CONFIRMED", "CANCELLED"]
                              : a.status === "CONFIRMED"
                                ? ["IN_PROGRESS", "CANCELLED"]
                                : ["COMPLETED", "CANCELLED"]
                            ).map((value) => ({ value, label: value })),
                          },
                          { name: "diagnosis", label: "Chẩn đoán kỹ thuật" },
                          {
                            name: "note",
                            label: "Ghi chú / lý do",
                            required: true,
                          },
                        ]}
                        submitLabel="Cập nhật tiến độ"
                        confirm
                        onSubmit={(v) =>
                          RepairOrdersService.ordersUpdateRepairStatus({
                            path: { repair_order_id: a.id },
                            body: {
                              status: v.status as
                                | "CONFIRMED"
                                | "IN_PROGRESS"
                                | "COMPLETED"
                                | "CANCELLED",
                              technician_diagnosis: v.diagnosis || undefined,
                              note: v.note,
                              cancellation_reason:
                                v.status === "CANCELLED" ? v.note : undefined,
                            },
                          })
                        }
                      />
                    )}{" "}
                    {active && reception && (
                      <ActionForm
                        key={`assign-${a.id}`}
                        fields={[
                          {
                            name: "technician",
                            label: "Kỹ thuật viên phụ trách",
                            required: true,
                            options:
                              techs.data?.data.map((t) => ({
                                value: t.id,
                                label: t.full_name,
                              })) ?? [],
                          },
                        ]}
                        submitLabel="Phân công kỹ thuật viên"
                        onSubmit={(v) =>
                          RepairOrdersService.ordersAssignTechnician({
                            path: { repair_order_id: a.id },
                            body: { technician_id: v.technician },
                          })
                        }
                      />
                    )}
                  </div>
                </div>
              </Panel>
              {a.device && (
                <Panel title="Thông tin thiết bị">
                  <ActionForm
                    key={a.device.id}
                    initial={{
                      brand: a.device.brand ?? "",
                      model: a.device.model ?? "",
                      imei: a.device.imei ?? "",
                      notes: a.device.notes ?? "",
                    }}
                    fields={[
                      { name: "brand", label: "Hãng", required: true },
                      { name: "model", label: "Dòng máy", required: true },
                      { name: "imei", label: "IMEI" },
                      { name: "notes", label: "Ghi chú thiết bị" },
                    ]}
                    submitLabel="Lưu thiết bị"
                    onSubmit={(v) =>
                      DevicesService.updateDevice({
                        path: { device_id: a.device?.id ?? "" },
                        body: {
                          brand: v.brand,
                          model: v.model,
                          imei: v.imei || null,
                          notes: v.notes || null,
                        },
                      })
                    }
                  />
                </Panel>
              )}
              {active && (
                <Panel title="Lập báo giá">
                  <ActionForm
                    key={a.id}
                    fields={quoteFields}
                    submitLabel="Tạo báo giá gửi khách"
                    onSubmit={(v) =>
                      QuotesService.createQuotation({
                        body: {
                          appointment_id: a.id,
                          status: "SENT",
                          items: Array.from({ length: items }, (_, i) => ({
                            item_name: v[`item_${i}`],
                            unit_price: Number(v[`price_${i}`]),
                            quantity: Number(v[`quantity_${i}`]),
                          })),
                        },
                      })
                    }
                  />
                  <Button
                    className="mt-3"
                    variant="outline"
                    disabled={items >= 20}
                    onClick={() => setItems(items + 1)}
                  >
                    Thêm hạng mục
                  </Button>
                </Panel>
              )}
              <QuotesPanel appointmentId={a.id} />
            </>
          )}
        </DataState>
      )}
    </section>
  )
}
