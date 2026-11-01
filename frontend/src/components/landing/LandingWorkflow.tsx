import type { LucideIcon } from "lucide-react"
import {
  BellRing,
  ClipboardCheck,
  MessageSquareText,
  Wrench,
} from "lucide-react"

interface WorkflowStep {
  icon: LucideIcon
  title: string
  description: string
}

const workflowSteps: WorkflowStep[] = [
  {
    icon: MessageSquareText,
    title: "Khách gửi yêu cầu",
    description: "Cung cấp thông tin liên hệ, thiết bị và nhu cầu sửa chữa.",
  },
  {
    icon: ClipboardCheck,
    title: "Cửa hàng tiếp nhận",
    description: "Nhân viên kiểm tra, xác nhận và tổ chức thông tin cần xử lý.",
  },
  {
    icon: Wrench,
    title: "Kỹ thuật viên xử lý",
    description:
      "Công việc được phân công và tiến độ được cập nhật theo quy trình.",
  },
  {
    icon: BellRing,
    title: "Cập nhật kết quả",
    description:
      "Khách hàng có cơ sở để theo dõi trạng thái và kết quả sửa chữa.",
  },
]

export function LandingWorkflow() {
  return (
    <section aria-labelledby="workflow-title" className="border-y bg-muted/40">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16 lg:px-8">
        <div className="max-w-xl">
          <p className="text-sm font-semibold tracking-wide text-primary uppercase">
            Cách vận hành
          </p>
          <h2
            id="workflow-title"
            className="mt-3 text-3xl font-bold tracking-tight text-balance sm:text-4xl"
          >
            Bốn bước để thông tin không bị bỏ sót.
          </h2>
          <p className="mt-4 text-lg leading-8 text-muted-foreground text-pretty">
            Đây là luồng nghiệp vụ FixCare hướng tới cho một yêu cầu sửa chữa,
            từ lúc khách liên hệ đến khi cửa hàng cập nhật kết quả.
          </p>
        </div>
        <ol className="grid gap-4 sm:grid-cols-2">
          {workflowSteps.map(({ icon: Icon, title, description }, index) => (
            <li key={title} className="rounded-2xl border bg-card p-5">
              <div className="flex items-center justify-between gap-3">
                <span className="grid size-10 place-items-center rounded-xl bg-primary text-primary-foreground">
                  <Icon aria-hidden="true" className="size-5" />
                </span>
                <span className="text-sm font-semibold text-muted-foreground">
                  0{index + 1}
                </span>
              </div>
              <h3 className="mt-5 text-lg font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {description}
              </p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
