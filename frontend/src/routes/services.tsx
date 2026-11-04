import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Clock, Search, ShieldCheck, Wrench } from "lucide-react"
import { useState } from "react"
import { ServicesService } from "@/client"
import { PublicLayout } from "@/components/Common/PublicLayout"
import { DataState, money, PageTitle } from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { pageHead } from "@/lib/seo"

export const Route = createFileRoute("/services")({
  component: PublicServices,
  head: pageHead("Dịch vụ sửa chữa"),
})

function PublicServices() {
  const [search, setSearch] = useState("")
  const list = useQuery({
    queryKey: ["services"],
    queryFn: async () => (await ServicesService.readPublicServices()).data,
  })

  const filteredServices = (list.data?.data ?? []).filter((service) => {
    const keyword = search.trim().toLowerCase()
    if (!keyword) return true
    return (
      service.name.toLowerCase().includes(keyword) ||
      (service.description ?? "").toLowerCase().includes(keyword)
    )
  })

  return (
    <PublicLayout>
      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <PageTitle
            title="Dịch vụ sửa chữa"
            description="Chọn dịch vụ bạn cần và đặt lịch ngay. Báo giá chính thức được xác nhận sau khi kiểm tra thiết bị."
          />
          <div className="relative w-full sm:max-w-xs">
            <Search
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Tìm dịch vụ..."
              aria-label="Tìm dịch vụ sửa chữa"
              className="pl-9"
            />
          </div>
        </div>

        <DataState
          pending={list.isPending}
          error={list.error}
          empty={!list.data?.count}
        >
          {filteredServices.length === 0 ? (
            <p className="mt-6 rounded-xl border bg-card p-6 text-sm text-muted-foreground">
              Không tìm thấy dịch vụ phù hợp với từ khóa &ldquo;{search}&rdquo;.
            </p>
          ) : (
            <div className="mt-6 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {filteredServices.map((s) => (
                <Card
                  key={s.id}
                  className="group flex flex-col justify-between transition-all duration-150 hover:border-primary/40 hover:shadow-md"
                >
                  <CardHeader className="space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
                        <Wrench aria-hidden="true" className="size-5" />
                      </span>
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:text-emerald-300">
                        <ShieldCheck aria-hidden="true" className="size-3.5" />
                        Bảo hành 6 tháng
                      </span>
                    </div>
                    <CardTitle className="text-lg">{s.name}</CardTitle>
                    <p className="text-sm font-semibold text-primary">
                      Từ {money(s.base_price ?? 0)} ·{" "}
                      <span className="inline-flex items-center gap-1 font-normal text-muted-foreground">
                        <Clock aria-hidden="true" className="size-3.5" />
                        Dự kiến {s.estimated_duration_minutes} phút
                      </span>
                    </p>
                  </CardHeader>
                  <CardContent className="flex flex-1 flex-col justify-between gap-4">
                    <p className="text-sm leading-relaxed text-muted-foreground">
                      {s.description ||
                        "Vui lòng liên hệ cửa hàng để tư vấn về dịch vụ này."}
                    </p>
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t">
                      <Button asChild size="sm">
                        <Link
                          to="/services/$serviceId"
                          params={{ serviceId: s.id }}
                        >
                          Xem dịch vụ
                        </Link>
                      </Button>
                      <Button asChild size="sm" variant="ghost">
                        <Link
                          to="/booking"
                          onClick={() =>
                            sessionStorage.setItem(
                              "fixphone_booking_service",
                              s.id,
                            )
                          }
                        >
                          Đặt lịch ngay →
                        </Link>
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </DataState>
      </section>
    </PublicLayout>
  )
}
