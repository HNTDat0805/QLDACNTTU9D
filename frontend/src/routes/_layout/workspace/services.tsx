import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { useState } from "react"
import { ServicesService, UsersService } from "@/client"
import {
  ActionForm,
  DataState,
  money,
  Pager,
  PageTitle,
  Panel,
} from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
export const Route = createFileRoute("/_layout/workspace/services")({
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    if (!user.is_superuser && !["admin", "manager"].includes(user.role ?? ""))
      throw redirect({ to: "/app" })
  },
  component: Services,
})
function Services() {
  const [page, setPage] = useState(0)
  const [selected, setSelected] = useState("")
  const list = useQuery({
    queryKey: ["operations", "services", page],
    queryFn: async () =>
      (
        await ServicesService.readManagedServices({
          query: { skip: page * 20, limit: 20 },
        })
      ).data,
  })
  const service = list.data?.data.find((s) => s.id === selected)
  return (
    <section className="space-y-6">
      <PageTitle
        title="Danh mục dịch vụ"
        description="Giá tham khảo và thời lượng dùng khi khách đặt lịch. Ngưng hoạt động thay cho xóa lịch sử."
      />
      <DataState
        pending={list.isPending}
        error={list.error}
        empty={!list.data?.count}
      >
        <div className="grid gap-4 md:grid-cols-2">
          {list.data?.data.map((s) => (
            <button
              key={s.id}
              type="button"
              className="rounded-xl border bg-card p-4 text-left"
              onClick={() => setSelected(s.id)}
            >
              <p className="font-semibold">{s.name}</p>
              <p>
                {money(s.base_price ?? 0)} · {s.estimated_duration_minutes} phút
              </p>
              <p className="text-sm text-muted-foreground">
                {s.is_active ? "Đang cung cấp" : "Ngừng cung cấp"}
              </p>
            </button>
          ))}
        </div>
      </DataState>
      <Pager page={page} count={list.data?.count ?? 0} setPage={setPage} />
      <Panel title={service ? `Cập nhật ${service.name}` : "Thêm dịch vụ"}>
        <ActionForm
          key={service?.id ?? "new"}
          fields={[
            { name: "name", label: "Tên dịch vụ", required: true },
            { name: "description", label: "Mô tả" },
            {
              name: "price",
              label: "Giá tham khảo (VNĐ)",
              type: "number",
              min: 0,
              required: true,
            },
            {
              name: "duration",
              label: "Thời lượng (phút)",
              type: "number",
              min: 1,
              max: 1440,
              required: true,
            },
            {
              name: "active",
              label: "Trạng thái",
              required: true,
              options: [
                { value: "true", label: "Đang cung cấp" },
                { value: "false", label: "Ngừng cung cấp" },
              ],
            },
          ]}
          initial={
            service
              ? {
                  name: service.name,
                  description: service.description ?? "",
                  price: String(service.base_price),
                  duration: String(service.estimated_duration_minutes),
                  active: String(service.is_active),
                }
              : { active: "true" }
          }
          submitLabel="Lưu dịch vụ"
          onSubmit={(v) => {
            const body = {
              name: v.name,
              description: v.description || null,
              base_price: Number(v.price),
              estimated_duration_minutes: Number(v.duration),
              is_active: v.active === "true",
            }
            return service
              ? ServicesService.updateService({
                  path: { service_id: service.id },
                  body,
                })
              : ServicesService.createService({ body })
          }}
        />
        {service && (
          <Button
            variant="ghost"
            className="mt-3"
            onClick={() => setSelected("")}
          >
            Thêm dịch vụ khác
          </Button>
        )}
      </Panel>
    </section>
  )
}
