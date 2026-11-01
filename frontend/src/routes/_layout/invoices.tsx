import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { CommerceService, QuotesService } from "@/client"
import {
  ActionForm,
  DataState,
  dateTime,
  money,
  Pager,
  PageTitle,
  Panel,
  Status,
} from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
export const Route = createFileRoute("/_layout/invoices")({
  component: Invoices,
})
function Invoices() {
  const { user } = useAuth()
  const staff =
    user?.is_superuser ||
    ["staff", "manager", "admin"].includes(user?.role ?? "")
  const [page, setPage] = useState(0)
  const [paymentKeys, setPaymentKeys] = useState<Record<string, string>>({})
  const invoices = useQuery({
    queryKey: ["operations", "invoices", page],
    queryFn: async () =>
      (
        await CommerceService.readInvoices({
          query: { skip: page * 20, limit: 20 },
        })
      ).data,
  })
  const quotes = useQuery({
    queryKey: ["operations", "invoice-quotes"],
    enabled: Boolean(staff),
    queryFn: async () =>
      (await QuotesService.readQuotations({ query: { limit: 100 } })).data,
  })
  return (
    <section className="space-y-6">
      <PageTitle
        title="Hóa đơn & thanh toán"
        description="Hóa đơn sửa chữa và lịch sử thu tiền tại cửa hàng."
      />
      {staff && (
        <Panel title="Lập hóa đơn từ báo giá">
          <ActionForm
            fields={[
              {
                name: "quote",
                label: "Báo giá đã duyệt",
                required: true,
                options:
                  quotes.data?.data
                    .filter((q) => q.status === "ACCEPTED")
                    .map((q) => ({
                      value: q.id,
                      label: `${q.quote_number} · ${q.appointment_number} · ${money(q.total_amount)}`,
                    })) ?? [],
              },
            ]}
            submitLabel="Lập hóa đơn"
            onSubmit={(v) =>
              CommerceService.issueInvoice({ body: { quote_id: v.quote } })
            }
          />
          <p className="mt-3 text-sm text-muted-foreground">
            Chỉ lập hóa đơn khi phiếu sửa chữa đã hoàn tất. Tổng tiền được lấy
            từ báo giá đã duyệt.
          </p>
        </Panel>
      )}
      <DataState
        pending={invoices.isPending}
        error={invoices.error}
        empty={!invoices.data?.count}
      >
        {invoices.data?.data.map((invoice) => (
          <Panel title={invoice.invoice_number} key={invoice.id}>
            <div className="mb-4 flex flex-wrap justify-between gap-3">
              <p>{dateTime(invoice.issue_date)}</p>
              <Status value={invoice.status ?? "UNPAID"} />
            </div>
            <ul className="space-y-2">
              {invoice.items.map((item) => (
                <li key={item.id} className="flex justify-between gap-3">
                  <span>
                    {item.item_name} × {item.quantity}
                  </span>
                  <span>{money(item.total_price ?? 0)}</span>
                </li>
              ))}
            </ul>
            <div className="my-4 grid gap-3 sm:grid-cols-3">
              <p>
                Tổng: <strong>{money(invoice.total_amount ?? 0)}</strong>
              </p>
              <p>
                Đã thu: <strong>{money(invoice.paid_amount)}</strong>
              </p>
              <p>
                Còn lại: <strong>{money(invoice.balance)}</strong>
              </p>
            </div>
            <div className="space-y-2">
              {invoice.payments.map((p) => (
                <p className="rounded-md bg-muted p-2 text-sm" key={p.id}>
                  {p.payment_number} · {money(p.amount)} · {p.payment_method} ·{" "}
                  {dateTime(p.paid_at)}
                </p>
              ))}
            </div>
            {staff && invoice.balance > 0 && invoice.status !== "CANCELLED" && (
              <div className="mt-5 max-w-lg">
                <ActionForm
                  fields={[
                    {
                      name: "amount",
                      label: "Số tiền đã nhận (VNĐ)",
                      type: "number",
                      min: 0.01,
                      max: invoice.balance,
                      required: true,
                    },
                    {
                      name: "method",
                      label: "Phương thức",
                      required: true,
                      options: [
                        { value: "CASH", label: "Tiền mặt" },
                        {
                          value: "BANK_TRANSFER",
                          label: "Chuyển khoản đã xác nhận",
                        },
                      ],
                    },
                    { name: "notes", label: "Ghi chú" },
                  ]}
                  submitLabel="Ghi nhận thanh toán"
                  confirm
                  onSubmit={async (v) => {
                    const signature = `${invoice.id}-${v.amount}-${v.method}`
                    const requestId =
                      paymentKeys[signature] ?? crypto.randomUUID()
                    setPaymentKeys((previous) => ({
                      ...previous,
                      [signature]: requestId,
                    }))
                    return CommerceService.recordPayment({
                      path: { invoice_id: invoice.id },
                      body: {
                        amount: v.amount,
                        payment_method: v.method as "CASH" | "BANK_TRANSFER",
                        request_id: requestId,
                        notes: v.notes || undefined,
                      },
                    })
                  }}
                />
              </div>
            )}
            {staff && invoice.status === "PAID" && (
              <div className="mt-4">
                <ActionForm
                  fields={[]}
                  submitLabel="Bàn giao thiết bị"
                  confirm
                  onSubmit={() =>
                    CommerceService.handoverDevice({
                      path: { invoice_id: invoice.id },
                    })
                  }
                />
              </div>
            )}
            <Button
              className="mt-4 print:hidden"
              variant="outline"
              onClick={() => window.print()}
            >
              In / lưu PDF danh sách hóa đơn
            </Button>
          </Panel>
        ))}
      </DataState>
      <Pager page={page} count={invoices.data?.count ?? 0} setPage={setPage} />
    </section>
  )
}
