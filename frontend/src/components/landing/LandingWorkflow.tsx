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
  step: string
}

const workflowSteps: WorkflowStep[] = [
  {
    icon: MessageSquareText,
    title: "Khách gửi yêu cầu",
    description: "Cung cấp thông tin liên hệ, thiết bị và nhu cầu sửa chữa qua ứng dụng.",
    step: "01",
  },
  {
    icon: ClipboardCheck,
    title: "Cửa hàng tiếp nhận",
    description: "Nhân viên kiểm tra, xác nhận và tổ chức thông tin cần xử lý.",
    step: "02",
  },
  {
    icon: Wrench,
    title: "Kỹ thuật viên xử lý",
    description: "Công việc được phân công và tiến độ cập nhật theo quy trình.",
    step: "03",
  },
  {
    icon: BellRing,
    title: "Cập nhật kết quả",
    description: "Khách hàng theo dõi trạng thái và nhận thông báo khi hoàn tất.",
    step: "04",
  },
]

export function LandingWorkflow() {
  return (
    <section
      aria-labelledby="workflow-title"
      className="bg-background"
    >
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
        {/* Header */}
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-widest text-primary">
            Cách vận hành
          </p>
          <h2
            id="workflow-title"
            className="mt-3 text-3xl font-bold tracking-tight text-balance sm:text-4xl"
          >
            Bốn bước để thông tin{" "}
            <span className="gradient-text-hero">không bị bỏ sót.</span>
          </h2>
          <p className="mt-4 text-lg leading-8 text-muted-foreground text-pretty">
            Từ lúc khách liên hệ đến khi cửa hàng trả máy — mọi bước đều có hệ thống ghi nhận.
          </p>
        </div>

        {/* Steps */}
        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {workflowSteps.map(({ icon: Icon, title, description, step }, index) => (
            <div key={title} className="relative flex flex-col">
              {/* Connector line between steps on large screens */}
              {index < workflowSteps.length - 1 && (
                <div
                  aria-hidden="true"
                  className="absolute left-full top-6 hidden h-px w-full -translate-y-1/2 lg:block"
                  style={{
                    background: "linear-gradient(90deg, oklch(0.585 0.233 275.8 / 40%), transparent)",
                  }}
                />
              )}

              {/* Card */}
              <div className="card-lift group flex flex-col rounded-2xl border bg-white p-6 shadow-sm h-full">
                {/* Step number + icon */}
                <div className="flex items-center justify-between mb-5">
                  <div className="grid size-12 place-items-center rounded-xl bg-primary text-white shadow-md shadow-primary/30 group-hover:scale-105 transition-transform duration-200">
                    <Icon aria-hidden="true" className="size-5" />
                  </div>
                  <span className="text-3xl font-black text-muted/30 tabular-nums select-none">
                    {step}
                  </span>
                </div>

                <h3 className="text-base font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground flex-1">
                  {description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
