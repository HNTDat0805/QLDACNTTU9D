import { createFileRoute, Link } from "@tanstack/react-router"
import { PublicLayout } from "@/components/Common/PublicLayout"
import { PageTitle, Panel } from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
export const Route = createFileRoute("/about")({ component: About })
function About() {
  return (
    <PublicLayout>
      <section className="mx-auto max-w-3xl space-y-6 px-4 py-12">
        <PageTitle
          title="Về FixCare"
          description="Kết nối khách hàng, nhân viên tiếp nhận và kỹ thuật viên trong một quy trình sửa chữa rõ ràng."
        />
        <Panel title="Theo dõi từ lúc đặt lịch đến bàn giao">
          <p className="leading-7 text-muted-foreground">
            Bạn có thể chọn dịch vụ và khung giờ còn trống, xem tiến độ sửa
            chữa, kiểm tra báo giá trước khi duyệt và xem hóa đơn sau khi hoàn
            tất. Nhân viên ghi nhận thanh toán và bàn giao tại cửa hàng.
          </p>
          <p className="mt-4 text-sm text-muted-foreground">
            FixCare là sản phẩm đồ án Quản lý dự án CNTT, phạm vi một cửa hàng
            sửa chữa điện thoại. Thông tin dịch vụ và thời gian trống được lấy
            từ hệ thống đang vận hành.
          </p>
          <Button asChild className="mt-6">
            <Link to="/services">Xem dịch vụ</Link>
          </Button>
        </Panel>
      </section>
    </PublicLayout>
  )
}
