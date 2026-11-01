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
export const Route = createFileRoute("/services_/$serviceId")({
  component: ServiceDetail,
})
function ServiceDetail() {
  const { serviceId } = Route.useParams()
  const service = useQuery({
    queryKey: ["service", serviceId],
    queryFn: async () =>
      (
        await ServicesService.readPublicService({
          path: { service_id: serviceId },
        })
      ).data,
  })
  return (
    <PublicLayout>
      <section className="mx-auto max-w-3xl px-4 py-12">
        <DataState pending={service.isPending} error={service.error}>
          {service.data && (
            <>
              <PageTitle
                title={service.data.name}
                description="Thông tin dịch vụ sửa chữa FixCare"
              />
              <Panel title="Chi tiết dịch vụ">
                <p>
                  {service.data.description ||
                    "Liên hệ nhân viên để được tư vấn tình trạng thiết bị và phương án sửa phù hợp."}
                </p>
                <p className="my-4 text-xl font-bold">
                  Giá tham khảo: {money(service.data.base_price ?? 0)}
                </p>
                <p className="mb-5">
                  Thời gian dự kiến: {service.data.estimated_duration_minutes}{" "}
                  phút. Giá chính thức được xác nhận qua báo giá sau kiểm tra.
                </p>
                <Button asChild>
                  <Link to="/booking">Đặt lịch sửa chữa</Link>
                </Button>
              </Panel>
            </>
          )}
        </DataState>
      </section>
    </PublicLayout>
  )
}
