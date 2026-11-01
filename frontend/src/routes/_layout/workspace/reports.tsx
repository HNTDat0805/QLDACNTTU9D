import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { useState } from "react"
import { CommerceService, UsersService } from "@/client"
import {
  DataState,
  money,
  PageTitle,
  Panel,
} from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
export const Route = createFileRoute("/_layout/workspace/reports")({
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    if (!user.is_superuser && !["admin", "manager"].includes(user.role ?? ""))
      throw redirect({ to: "/app" })
  },
  component: Reports,
})
function Reports() {
  const [start, setStart] = useState("")
  const [end, setEnd] = useState("")
  const report = useQuery({
    queryKey: ["operations", "statistics", start, end],
    queryFn: async () =>
      (
        await CommerceService.readStatistics({
          query: { start_date: start || undefined, end_date: end || undefined },
        })
      ).data,
  })
  const data = report.data
  const max = Math.max(1, ...(data?.monthly_revenue.map((m) => m.amount) ?? []))
  return (
    <section className="space-y-6">
      <PageTitle
        title="Báo cáo quản trị"
        description="Doanh thu là tổng các khoản đã thu thành công, không phải giá trị lịch hẹn."
      />
      <div className="flex flex-wrap gap-3">
        <Input
          className="max-w-xs"
          type="date"
          aria-label="Từ ngày"
          value={start}
          onChange={(e) => setStart(e.target.value)}
        />
        <Input
          className="max-w-xs"
          type="date"
          aria-label="Đến ngày"
          value={end}
          onChange={(e) => setEnd(e.target.value)}
        />
      </div>
      <DataState pending={report.isPending} error={report.error}>
        {data && (
          <>
            <p className="text-sm text-muted-foreground">
              Kỳ {data.start_date} – {data.end_date}
            </p>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {[
                { name: "Đã thu trong kỳ", value: money(data.receipts_total) },
                {
                  name: "Công nợ toàn hệ thống",
                  value: money(data.outstanding_total),
                },
                { name: "Lịch hẹn trong kỳ", value: data.appointment_count },
                { name: "Hoàn tất trong kỳ", value: data.completed_count },
              ].map((m) => (
                <Panel key={m.name} title={m.name}>
                  <p className="text-2xl font-bold">{m.value}</p>
                </Panel>
              ))}
            </div>
            <Panel title="Doanh thu theo tháng">
              <div className="space-y-4">
                {data.monthly_revenue.map((m) => (
                  <div key={m.month}>
                    <div className="mb-1 flex justify-between gap-3 text-sm">
                      <span>{m.month}</span>
                      <span>{money(m.amount)}</span>
                    </div>
                    <div className="h-3 rounded-full bg-muted">
                      <div
                        className="h-3 rounded-full bg-primary"
                        style={{ width: `${(m.amount / max) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </Panel>
            <Button
              variant="outline"
              onClick={() => {
                const csv = [
                  "Thang,Doanh thu",
                  ...data.monthly_revenue.map((m) => `${m.month},${m.amount}`),
                ].join("\n")
                const url = URL.createObjectURL(
                  new Blob([csv], { type: "text/csv;charset=utf-8" }),
                )
                const link = document.createElement("a")
                link.href = url
                link.download = "fixcare-revenue.csv"
                link.click()
                URL.revokeObjectURL(url)
              }}
            >
              Xuất báo cáo CSV
            </Button>
          </>
        )}
      </DataState>
    </section>
  )
}
