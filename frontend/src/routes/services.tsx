import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ServicesService } from "@/client"
import { PublicLayout } from "@/components/Common/PublicLayout"
import {
  DataState,
  money,
  PageTitle,
  Panel,
} from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
export const Route = createFileRoute("/services")({ component: PublicServices })
function PublicServices() {
  const list = useQuery({
    queryKey: ["services"],
    queryFn: async () => (await ServicesService.readPublicServices()).data,
  })
  return (
    <PublicLayout>
      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <PageTitle
          title="Dịch vụ sửa chữa"
          description="Giá tham khảo; báo giá chính thức được xác nhận sau khi kiểm tra thiết bị."
        />
        <DataState
          pending={list.isPending}
          error={list.error}
          empty={!list.data?.count}
        >
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {list.data?.data.map((s) => (
              <Panel key={s.id} title={s.name}>
                <p className="mb-3 text-sm text-muted-foreground">
                  {s.description ||
                    "Vui lòng liên hệ cửa hàng để tư vấn về dịch vụ này."}
                </p>
                <p className="font-semibold">{money(s.base_price ?? 0)}</p>
                <p className="mb-4 text-sm">
                  Dự kiến {s.estimated_duration_minutes} phút
                </p>
                <Button asChild>
                  <Link to="/services/$serviceId" params={{ serviceId: s.id }}>
                    Xem dịch vụ
                  </Link>
                </Button>
              </Panel>
            ))}
          </div>
        </DataState>
      </section>
    </PublicLayout>
  )
}
