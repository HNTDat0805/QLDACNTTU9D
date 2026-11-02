import type { LucideIcon } from "lucide-react"
import {
  CalendarClock,
  ClipboardList,
  Smartphone,
  UsersRound,
} from "lucide-react"

interface Feature {
  icon: LucideIcon
  title: string
  description: string
  iconColor: string
  iconBg: string
}

const features: Feature[] = [
  {
    icon: CalendarClock,
    title: "Tổ chức lịch hẹn",
    description:
      "Đặt lịch nhanh, ghi nhận thời gian và thiết bị trước khi cửa hàng tiếp nhận.",
    iconColor: "text-indigo-600",
    iconBg: "bg-indigo-50",
  },
  {
    icon: Smartphone,
    title: "Quản lý thiết bị tập trung",
    description:
      "Thông tin điện thoại và tình trạng ban đầu gắn liền với yêu cầu sửa chữa.",
    iconColor: "text-violet-600",
    iconBg: "bg-violet-50",
  },
  {
    icon: ClipboardList,
    title: "Theo dõi tiến độ rõ ràng",
    description:
      "Các bước tiếp nhận, xử lý và kết quả trình bày minh bạch, dễ tra cứu.",
    iconColor: "text-purple-600",
    iconBg: "bg-purple-50",
  },
  {
    icon: UsersRound,
    title: "Phối hợp đúng vai trò",
    description:
      "Khách hàng, nhân viên, kỹ thuật viên và quản lý cùng làm việc hiệu quả.",
    iconColor: "text-primary",
    iconBg: "bg-primary/10",
  },
]

export function LandingFeatures() {
  return (
    <section
      aria-labelledby="features-title"
      className="bg-white border-y"
    >
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
        {/* Section header */}
        <div className="max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-widest text-primary">
            Giá trị định hướng
          </p>
          <h2
            id="features-title"
            className="mt-3 text-3xl font-bold tracking-tight text-balance sm:text-4xl"
          >
            Một quy trình sửa chữa dễ hiểu{" "}
            <span className="gradient-text-hero">từ đầu đến cuối.</span>
          </h2>
          <p className="mt-4 text-lg leading-8 text-muted-foreground text-pretty">
            FixPhone được thiết kế để giảm thao tác thủ công và giúp thông tin
            sửa chữa được theo dõi có hệ thống.
          </p>
        </div>

        {/* Features grid */}
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ icon: Icon, title, description, iconColor, iconBg }) => (
            <div
              key={title}
              className="card-lift group rounded-2xl border bg-white p-6 shadow-sm"
            >
              <span
                className={`grid size-12 place-items-center rounded-xl ${iconBg} ${iconColor} transition-all duration-200 group-hover:scale-110`}
              >
                <Icon aria-hidden="true" className="size-5" />
              </span>
              <h3 className="mt-5 text-base font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
