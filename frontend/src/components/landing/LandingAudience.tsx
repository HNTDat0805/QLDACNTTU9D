import type { LucideIcon } from "lucide-react"
import { CircleUserRound, Headset, Wrench } from "lucide-react"

interface AudienceBenefit {
  icon: LucideIcon
  role: string
  title: string
  description: string
}

const audienceBenefits: AudienceBenefit[] = [
  {
    icon: CircleUserRound,
    role: "Khách hàng",
    title: "Biết mình cần chuẩn bị gì",
    description:
      "Có một nơi thống nhất để cung cấp thông tin thiết bị và theo dõi yêu cầu sửa chữa.",
  },
  {
    icon: Headset,
    role: "Nhân viên tiếp nhận",
    title: "Dễ tổ chức thông tin hơn",
    description:
      "Giảm việc đối chiếu thông tin rời rạc khi tiếp nhận và cập nhật yêu cầu.",
  },
  {
    icon: Wrench,
    role: "Kỹ thuật viên và quản lý",
    title: "Tập trung vào công việc phù hợp",
    description:
      "Theo dõi nội dung liên quan đến xử lý, tiến độ và điều phối công việc trong cửa hàng.",
  },
]

export function LandingAudience() {
  return (
    <section
      aria-labelledby="audience-title"
      className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8"
    >
      <div className="max-w-2xl">
        <p className="text-sm font-semibold tracking-wide text-primary uppercase">
          Phù hợp từng vai trò
        </p>
        <h2
          id="audience-title"
          className="mt-3 text-3xl font-bold tracking-tight text-balance sm:text-4xl"
        >
          Cùng một quy trình, mỗi người có thông tin cần thiết.
        </h2>
      </div>
      <div className="mt-10 grid gap-5 lg:grid-cols-3">
        {audienceBenefits.map(({ icon: Icon, role, title, description }) => (
          <article
            key={role}
            className="rounded-2xl border bg-card p-6 shadow-sm"
          >
            <span className="inline-flex items-center gap-2 text-sm font-semibold text-primary">
              <Icon aria-hidden="true" className="size-4" />
              {role}
            </span>
            <h3 className="mt-5 text-xl font-semibold tracking-tight">
              {title}
            </h3>
            <p className="mt-3 leading-7 text-muted-foreground">
              {description}
            </p>
          </article>
        ))}
      </div>
    </section>
  )
}
