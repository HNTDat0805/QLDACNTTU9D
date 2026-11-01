import { createFileRoute } from "@tanstack/react-router"
import { QuotesPanel } from "@/components/Operations/QuotesPanel"
import { PageTitle } from "@/components/Operations/shared"
export const Route = createFileRoute("/_layout/quotes")({ component: MyQuotes })
function MyQuotes() {
  return (
    <section>
      <PageTitle
        title="Báo giá sửa chữa"
        description="Kiểm tra từng hạng mục và xác nhận trước khi sửa chữa."
      />
      <QuotesPanel />
    </section>
  )
}
