import { Link } from "@tanstack/react-router"
import { ArrowRight, CalendarClock, Smartphone } from "lucide-react"

import { Button } from "@/components/ui/button"

export function LandingCta() {
  return (
    <section aria-labelledby="cta-title" className="bg-card border-t">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
        <div className="relative overflow-hidden rounded-3xl bg-primary px-6 py-12 sm:px-12 sm:py-16 lg:flex lg:items-center lg:justify-between lg:gap-16">
          {/* Decorations */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0"
          >
            <div className="absolute -top-24 -right-24 h-80 w-80 rounded-full bg-white/8 blur-3xl" />
            <div className="absolute -bottom-12 -left-12 h-60 w-60 rounded-full bg-violet-600/30 blur-3xl" />
            <div
              className="absolute inset-0 opacity-[0.04]"
              style={{
                backgroundImage: `url("data:image/svg+xml,%3Csvg width='32' height='32' viewBox='0 0 32 32' xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='2' cy='2' r='1.5' fill='white'/%3E%3C/svg%3E")`,
                backgroundSize: "32px 32px",
              }}
            />
          </div>

          {/* Content */}
          <div className="relative max-w-2xl">
            <div className="flex flex-wrap items-center gap-3 mb-5">
              <span className="grid size-12 place-items-center rounded-2xl bg-white/15 backdrop-blur-sm">
                <Smartphone aria-hidden="true" className="size-6 text-white" />
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-4 py-1.5 text-sm font-medium text-white">
                <CalendarClock aria-hidden="true" className="size-3.5" />
                Sẵn sàng hoạt động
              </span>
            </div>

            <h2
              id="cta-title"
              className="text-3xl font-bold tracking-tight text-white text-balance sm:text-4xl lg:text-5xl"
            >
              Sẵn sàng khám phá FixPhone?
            </h2>
            <p className="mt-4 text-base leading-7 text-white/80 sm:text-lg max-w-xl">
              Tạo tài khoản để đặt lịch sửa chữa, hoặc đăng nhập nếu bạn đã có
              quyền truy cập hệ thống.
            </p>
          </div>

          {/* Buttons */}
          <div className="relative mt-8 flex flex-col gap-3 sm:flex-row lg:mt-0 lg:shrink-0">
            <Button
              asChild
              size="lg"
              className="w-full bg-white text-primary hover:bg-white/92 shadow-lg font-semibold rounded-xl transition-all duration-200 hover:scale-[1.02] sm:w-auto"
            >
              <Link to="/booking">
                <CalendarClock aria-hidden="true" className="size-4" />
                Đặt lịch ngay
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="w-full border-white/30 bg-transparent text-white hover:bg-white/12 hover:text-white hover:border-white/50 font-semibold rounded-xl transition-all duration-200 sm:w-auto"
            >
              <Link to="/signup">Tạo tài khoản</Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="w-full border-white/30 bg-transparent text-white hover:bg-white/12 hover:text-white hover:border-white/50 font-semibold rounded-xl transition-all duration-200 sm:w-auto"
            >
              <Link to="/login">Đăng nhập</Link>
            </Button>
          </div>
        </div>
      </div>
    </section>
  )
}
