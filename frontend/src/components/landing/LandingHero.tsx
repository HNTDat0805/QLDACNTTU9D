import { Link } from "@tanstack/react-router"
import {
  CalendarCheck2,
  ClipboardCheck,
  ShieldCheck,
  Wrench,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

const journeyItems = [
  {
    icon: CalendarCheck2,
    label: "Yêu cầu được ghi nhận",
    detail: "Thông tin lịch hẹn và thiết bị",
  },
  {
    icon: Wrench,
    label: "Quy trình được phối hợp",
    detail: "Tiếp nhận, xử lý, cập nhật",
  },
  {
    icon: ClipboardCheck,
    label: "Trạng thái dễ theo dõi",
    detail: "Mỗi bước có thông tin rõ ràng",
  },
]

export function LandingHero() {
  return (
    <section
      aria-labelledby="landing-title"
      className="overflow-hidden border-b bg-muted/30"
    >
      <div className="mx-auto grid max-w-7xl gap-12 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:gap-16 lg:px-8 lg:py-28">
        <div className="max-w-2xl">
          <Badge
            variant="outline"
            className="border-primary/30 bg-primary/5 px-3 py-1 text-primary"
          >
            <ShieldCheck aria-hidden="true" />
            Quy trình sửa chữa có tổ chức
          </Badge>
          <h1
            id="landing-title"
            className="mt-5 text-4xl font-bold tracking-tight text-balance sm:text-5xl lg:text-6xl lg:leading-tight"
          >
            Gửi gắm thiết bị, theo dõi sửa chữa thật rõ ràng.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-8 text-muted-foreground text-pretty">
            FixCare hướng tới việc kết nối khách hàng, nhân viên và kỹ thuật
            viên trong một quy trình tiếp nhận và sửa chữa điện thoại dễ hiểu.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg" className="w-full sm:w-auto">
              <Link to="/signup">Tạo tài khoản</Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="w-full sm:w-auto"
            >
              <Link to="/login">Đăng nhập</Link>
            </Button>
          </div>
          <p className="mt-4 text-sm text-muted-foreground">
            Bắt đầu bằng tài khoản FixCare để vào đúng khu vực làm việc của bạn.
          </p>
        </div>
        <RepairJourneyVisual />
      </div>
    </section>
  )
}

function RepairJourneyVisual() {
  return (
    <aside
      aria-label="Minh họa quy trình tiếp nhận và sửa chữa điện thoại"
      className="relative mx-auto w-full max-w-lg"
    >
      <div className="absolute -inset-6 -z-10 rounded-[2rem] bg-primary/10 blur-3xl" />
      <div className="rounded-3xl border bg-card p-4 shadow-sm sm:p-6">
        <div className="flex items-center justify-between border-b pb-4">
          <div>
            <p className="text-sm font-semibold">Hành trình sửa chữa</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Thông tin được tổ chức theo từng bước
            </p>
          </div>
          <span className="grid size-11 place-items-center rounded-2xl bg-primary text-primary-foreground">
            <Wrench aria-hidden="true" className="size-5" />
          </span>
        </div>
        <ol className="mt-5 space-y-3">
          {journeyItems.map(({ icon: Icon, label, detail }, index) => (
            <li
              key={label}
              className="flex items-center gap-3 rounded-2xl border bg-background p-3 motion-safe:transition-transform motion-safe:duration-200 hover:translate-x-1"
            >
              <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary/10 text-sm font-bold text-primary">
                {index + 1}
              </span>
              <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-muted text-primary">
                <Icon aria-hidden="true" className="size-4" />
              </span>
              <span className="min-w-0">
                <span className="block font-medium">{label}</span>
                <span className="mt-0.5 block text-sm text-muted-foreground">
                  {detail}
                </span>
              </span>
            </li>
          ))}
        </ol>
      </div>
    </aside>
  )
}
