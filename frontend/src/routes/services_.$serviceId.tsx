import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { CheckCircle2, Clock, ShieldCheck } from "lucide-react"
import { ServicesService } from "@/client"
import { PublicLayout } from "@/components/Common/PublicLayout"
import {
  DataState,
  money,
  PageTitle,
  Panel,
} from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
import { APP_NAME, pageHead } from "@/lib/seo"

export const Route = createFileRoute("/services_/$serviceId")({
  component: ServiceDetail,
  head: pageHead("Chi tiết dịch vụ"),
})

const includedBenefits = [
  "Kiểm tra thiết bị miễn phí trước khi sửa chữa",
  "Linh kiện đạt chuẩn chất lượng, nguồn gốc rõ ràng",
  "Vệ sinh máy miễn phí sau khi hoàn tất",
  "Bảo hành 6 tháng cho hạng mục thay thế",
]

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
      <section className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
        <div className="mb-4">
          <Button asChild variant="ghost" size="sm">
            <Link to="/services">← Quay lại danh sách dịch vụ</Link>
          </Button>
        </div>
        <DataState pending={service.isPending} error={service.error}>
          {service.data && (
            <>
              <PageTitle
                title={service.data.name}
                description={`Thông tin dịch vụ sửa chữa ${APP_NAME}`}
              />
              <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_340px]">
                <Panel title="Chi tiết dịch vụ">
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                    Mô tả dịch vụ
                  </h3>
                  <p className="mt-2 leading-relaxed">
                    {service.data.description ||
                      "Liên hệ nhân viên để được tư vấn tình trạng thiết bị và phương án sửa phù hợp."}
                  </p>
                  <div className="mt-6 border-t pt-5">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                      Bao gồm quyền lợi
                    </h3>
                    <ul className="mt-3 space-y-2.5">
                      {includedBenefits.map((benefit) => (
                        <li
                          key={benefit}
                          className="flex items-center gap-2.5 text-sm"
                        >
                          <CheckCircle2
                            aria-hidden="true"
                            className="size-4 shrink-0 text-emerald-600"
                          />
                          <span>{benefit}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </Panel>

                <Panel title="Tóm tắt chi phí & thời gian">
                  <p className="text-sm text-muted-foreground">Giá tham khảo</p>
                  <p className="my-2 text-2xl font-bold text-primary">
                    Từ {money(service.data.base_price ?? 0)}
                  </p>
                  <div className="my-4 space-y-2 rounded-lg bg-muted/50 p-3 text-sm">
                    <p className="flex items-center gap-2">
                      <Clock
                        aria-hidden="true"
                        className="size-4 text-primary"
                      />
                      Thời gian dự kiến:{" "}
                      <strong>
                        {service.data.estimated_duration_minutes} phút
                      </strong>
                    </p>
                    <p className="flex items-center gap-2">
                      <ShieldCheck
                        aria-hidden="true"
                        className="size-4 text-emerald-600"
                      />
                      Bảo hành 6 tháng tại cửa hàng FixPhone
                    </p>
                  </div>
                  <p className="mb-5 text-xs text-muted-foreground">
                    Giá chính thức được xác nhận qua báo giá sau kiểm tra.
                  </p>
                  <Button asChild className="w-full">
                    <Link
                      to="/booking"
                      onClick={() =>
                        sessionStorage.setItem(
                          "fixphone_booking_service",
                          serviceId,
                        )
                      }
                    >
                      Đặt lịch sửa chữa
                    </Link>
                  </Button>
                </Panel>
              </div>
            </>
          )}
        </DataState>
      </section>
    </PublicLayout>
  )
}
