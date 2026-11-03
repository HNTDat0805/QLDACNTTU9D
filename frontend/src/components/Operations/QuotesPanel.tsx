import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { QuotesService } from "@/client"
import { ActionForm, DataState, money, Pager, Panel, Status } from "./shared"

export function QuotesPanel({ appointmentId }: { appointmentId?: string }) {
  const [page, setPage] = useState(0)
  const quotes = useQuery({
    queryKey: ["operations", "quotes", appointmentId, page],
    queryFn: async () =>
      (
        await QuotesService.readQuotations({
          query: { appointment_id: appointmentId, skip: page * 20, limit: 20 },
        })
      ).data,
  })
  return (
    <div className="space-y-4">
      <DataState
        pending={quotes.isPending}
        error={quotes.error}
        empty={!quotes.data?.count}
      >
        {quotes.data?.data.map((quote) => (
          <Panel key={quote.id} title={quote.quote_number}>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <span className="text-sm font-medium text-muted-foreground">
                Đơn sửa chữa: <strong>{quote.appointment_number}</strong> ·{" "}
                {quote.device_info}
              </span>
              <Status value={quote.status} />
            </div>

            {/* Line Items Table (Figma KH17) */}
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-left text-sm">
                <thead className="border-b bg-muted/50 text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Hạng mục</th>
                    <th className="px-3 py-2 text-right">SL</th>
                    <th className="px-3 py-2 text-right">Đơn giá</th>
                    <th className="px-3 py-2 text-right">Thành tiền</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {quote.items?.map((item) => (
                    <tr key={item.id}>
                      <td className="px-3 py-2.5 font-medium">
                        {item.item_name} × {item.quantity}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        {item.quantity}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        {money(item.unit_price)}
                      </td>
                      <td className="px-3 py-2.5 text-right font-semibold">
                        {money(item.total_price)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="my-4 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-primary/5 p-3">
              <span className="text-xs text-muted-foreground">
                Bảo hành 6 tháng linh kiện thay thế · Báo giá minh bạch trước
                khi sửa
              </span>
              <p className="text-lg font-bold text-primary">
                Tổng báo giá: {money(quote.total_amount)}
              </p>
            </div>

            {["DRAFT", "SENT"].includes(quote.status) && (
              <div className="grid gap-5 sm:grid-cols-2">
                <ActionForm
                  fields={[]}
                  submitLabel="Duyệt báo giá"
                  confirm
                  onSubmit={() =>
                    QuotesService.acceptQuotation({
                      path: { quote_id: quote.id },
                    })
                  }
                />
                <ActionForm
                  fields={[
                    { name: "note", label: "Lý do từ chối", required: true },
                  ]}
                  submitLabel="Từ chối báo giá"
                  confirm
                  onSubmit={(v) =>
                    QuotesService.rejectQuotation({
                      path: { quote_id: quote.id },
                      body: { note: v.note },
                    })
                  }
                />
              </div>
            )}
          </Panel>
        ))}
      </DataState>
      <Pager page={page} count={quotes.data?.count ?? 0} setPage={setPage} />
    </div>
  )
}
