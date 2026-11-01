import type { LucideIcon } from "lucide-react"
import {
  CalendarClock,
  ClipboardList,
  Smartphone,
  UsersRound,
} from "lucide-react"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

interface Feature {
  icon: LucideIcon
  title: string
  description: string
}

const features: Feature[] = [
  {
    icon: CalendarClock,
    title: "Tổ chức lịch hẹn",
    description:
      "Hướng tới quy trình ghi nhận thời gian và thông tin cần thiết trước khi cửa hàng tiếp nhận thiết bị.",
  },
  {
    icon: Smartphone,
    title: "Quản lý thiết bị tập trung",
    description:
      "Thông tin điện thoại và tình trạng ban đầu được đặt trong cùng bối cảnh của yêu cầu sửa chữa.",
  },
  {
    icon: ClipboardList,
    title: "Theo dõi tiến độ rõ ràng",
    description:
      "Các bước tiếp nhận, xử lý và kết quả được định hướng trình bày minh bạch, dễ tra cứu.",
  },
  {
    icon: UsersRound,
    title: "Phối hợp đúng vai trò",
    description:
      "Khách hàng, nhân viên, kỹ thuật viên và quản lý tập trung vào thông tin phù hợp với công việc của mình.",
  },
]

export function LandingFeatures() {
  return (
    <section
      aria-labelledby="features-title"
      className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8"
    >
      <div className="max-w-2xl">
        <p className="text-sm font-semibold tracking-wide text-primary uppercase">
          Giá trị định hướng
        </p>
        <h2
          id="features-title"
          className="mt-3 text-3xl font-bold tracking-tight text-balance sm:text-4xl"
        >
          Một quy trình sửa chữa dễ hiểu từ đầu đến cuối.
        </h2>
        <p className="mt-4 text-lg leading-8 text-muted-foreground text-pretty">
          FixCare được thiết kế để giảm thao tác thủ công và giúp thông tin sửa
          chữa được theo dõi có hệ thống.
        </p>
      </div>
      <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {features.map(({ icon: Icon, title, description }) => (
          <Card
            key={title}
            className="gap-0 rounded-2xl py-0 shadow-none motion-safe:transition-transform motion-safe:duration-200 hover:-translate-y-1 hover:border-primary/35"
          >
            <CardHeader className="px-5 pt-5">
              <span className="grid size-11 place-items-center rounded-xl bg-primary/10 text-primary">
                <Icon aria-hidden="true" className="size-5" />
              </span>
              <CardTitle className="mt-5 text-lg">{title}</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-5">
              <CardDescription className="leading-6">
                {description}
              </CardDescription>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  )
}
