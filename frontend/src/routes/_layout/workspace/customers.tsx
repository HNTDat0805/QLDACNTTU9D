import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { CustomersService } from "@/client"
import {
  ActionForm,
  DataState,
  Pager,
  PageTitle,
  Panel,
} from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export const Route = createFileRoute("/_layout/workspace/customers")({
  component: Customers,
})
function Customers() {
  const [q, setQ] = useState("")
  const [page, setPage] = useState(0)
  const [selected, setSelected] = useState("")
  const list = useQuery({
    queryKey: ["operations", "customers", q, page],
    queryFn: async () =>
      (
        await CustomersService.readCustomers({
          query: { q: q || undefined, skip: page * 20, limit: 20 },
        })
      ).data,
  })
  const customer = list.data?.data.find((c) => c.id === selected)
  const fields = [
    { name: "full_name", label: "Họ tên", required: true },
    {
      name: "phone_number",
      label: "Số điện thoại",
      required: true,
      type: "tel" as const,
    },
    { name: "email", label: "Email", type: "email" as const },
    { name: "address", label: "Địa chỉ" },
  ]
  return (
    <section className="space-y-6">
      <PageTitle
        title="Khách hàng"
        description="Hồ sơ liên hệ để tiếp nhận và theo dõi sửa chữa."
      />
      <Input
        className="max-w-md"
        aria-label="Tìm khách hàng"
        placeholder="Tên, email hoặc số điện thoại"
        value={q}
        onChange={(e) => {
          setQ(e.target.value)
          setPage(0)
        }}
      />
      <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <div>
          <DataState
            pending={list.isPending}
            error={list.error}
            empty={!list.data?.count}
          >
            <div className="grid gap-3">
              {list.data?.data.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setSelected(c.id)}
                  className="rounded-lg border bg-card p-4 text-left hover:border-primary"
                >
                  <p className="font-semibold">{c.full_name}</p>
                  <p className="text-sm text-muted-foreground">
                    {c.phone_number} · {c.email || "Chưa có email"}
                  </p>
                </button>
              ))}
            </div>
          </DataState>
          <Pager page={page} count={list.data?.count ?? 0} setPage={setPage} />
        </div>
        <Panel title={customer ? "Cập nhật khách hàng" : "Thêm khách hàng"}>
          <ActionForm
            key={customer?.id ?? "new"}
            fields={fields}
            initial={
              customer
                ? {
                    full_name: customer.full_name,
                    phone_number: customer.phone_number,
                    email: customer.email ?? "",
                    address: customer.address ?? "",
                  }
                : {}
            }
            submitLabel={customer ? "Lưu hồ sơ" : "Tạo khách hàng"}
            onSubmit={(v) =>
              customer
                ? CustomersService.updateCustomer({
                    path: { customer_id: customer.id },
                    body: {
                      full_name: v.full_name,
                      phone_number: v.phone_number,
                      email: v.email || null,
                      address: v.address || null,
                    },
                  })
                : CustomersService.createCustomer({
                    body: {
                      full_name: v.full_name,
                      phone_number: v.phone_number,
                      email: v.email || null,
                      address: v.address || null,
                    },
                  })
            }
          />
          {customer && (
            <Button
              variant="ghost"
              className="mt-3"
              onClick={() => setSelected("")}
            >
              Thêm khách khác
            </Button>
          )}
        </Panel>
      </div>
    </section>
  )
}
