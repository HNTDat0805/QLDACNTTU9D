import { Link } from "@tanstack/react-router"
import { ArrowRight, Smartphone } from "lucide-react"

import { Button } from "@/components/ui/button"

export function LandingCta() {
  return (
    <section
      aria-labelledby="cta-title"
      className="px-4 pb-16 sm:px-6 sm:pb-24 lg:px-8"
    >
      <div className="mx-auto max-w-7xl rounded-3xl bg-primary px-6 py-10 text-primary-foreground sm:px-10 sm:py-14 lg:flex lg:items-center lg:justify-between lg:gap-12">
        <div className="max-w-2xl">
          <span className="grid size-11 place-items-center rounded-2xl bg-primary-foreground/15">
            <Smartphone aria-hidden="true" className="size-5" />
          </span>
          <h2
            id="cta-title"
            className="mt-5 text-3xl font-bold tracking-tight text-balance sm:text-4xl"
          >
            Sẵn sàng khám phá FixCare?
          </h2>
          <p className="mt-3 text-base leading-7 text-primary-foreground/85 sm:text-lg">
            Tạo tài khoản để bắt đầu, hoặc đăng nhập nếu bạn đã có quyền truy
            cập.
          </p>
        </div>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row lg:mt-0 lg:shrink-0">
          <Button
            asChild
            size="lg"
            variant="secondary"
            className="w-full sm:w-auto"
          >
            <Link to="/signup">
              Tạo tài khoản
              <ArrowRight aria-hidden="true" />
            </Link>
          </Button>
          <Button
            asChild
            size="lg"
            variant="outline"
            className="w-full border-primary-foreground/30 bg-transparent text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground sm:w-auto"
          >
            <Link to="/login">Đăng nhập</Link>
          </Button>
        </div>
      </div>
    </section>
  )
}
