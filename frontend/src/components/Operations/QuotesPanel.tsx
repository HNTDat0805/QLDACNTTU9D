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
            <div className="mb-4 flex flex-wrap justify-between gap-3">
              <span>
                {quote.appointment_number} · {quote.device_info}
              </span>
              <Status value={quote.status} />
            </div>
            <ul className="space-y-2">
              {quote.items?.map((item) => (
                <li
                  key={item.id}
                  className="flex justify-between gap-3 text-sm"
                >
                  <span>
                    {item.item_name} × {item.quantity}
                  </span>
                  <span>{money(item.total_price)}</span>
                </li>
              ))}
            </ul>
            <p className="my-4 text-lg font-bold">
              Tổng báo giá: {money(quote.total_amount)}
            </p>
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
