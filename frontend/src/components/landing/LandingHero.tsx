import { Link } from "@tanstack/react-router"
import {
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  Smartphone,
  Star,
  Wrench,
  Zap,
} from "lucide-react"

import { Button } from "@/components/ui/button"

const trustItems = [
  "Đặt lịch chỉ 1 phút",
  "Theo dõi trực tiếp",
  "Kỹ thuật viên chuyên nghiệp",
]

const quickServices = [
  { icon: Smartphone, label: "Thay pin", price: "Từ 150K" },
  { icon: Wrench, label: "Thay màn hình", price: "Từ 350K" },
  { icon: ClipboardCheck, label: "Sửa nguồn / main", price: "Từ 200K" },
  { icon: CalendarClock, label: "Đặt lịch sửa", price: "Miễn phí" },
]

export function LandingHero() {
  return (
    <section
      aria-labelledby="landing-title"
      className="relative overflow-hidden hero-mesh"
    >
      {/* Dot pattern overlay */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 dot-pattern opacity-50"
      />

      <div className="relative mx-auto max-w-7xl px-4 pb-20 pt-16 sm:px-6 sm:pb-28 sm:pt-20 lg:px-8 lg:pb-32 lg:pt-24">
        <div className="grid items-center gap-12 lg:grid-cols-[1fr_480px] lg:gap-16">
          {/* Left column */}
          <div className="max-w-2xl">
            {/* Badge */}
            <span className="badge-indigo">
              <Star aria-hidden="true" className="size-3.5 fill-current" />
              Nền tảng sửa chữa điện thoại số 1
            </span>

            <h1
              id="landing-title"
              className="mt-6 text-4xl font-bold tracking-tight text-balance sm:text-5xl lg:text-[3.5rem] lg:leading-[1.08]"
            >
              Sửa điện thoại nhanh,{" "}
              <span className="gradient-text-hero">
                đặt lịch chỉ 1 phút
              </span>
            </h1>

            <p className="mt-5 text-lg leading-relaxed text-muted-foreground max-w-lg text-pretty">
              Chọn dịch vụ, chọn ngày giờ, nhận thông báo tức thì — quy trình sửa chữa
              điện thoại minh bạch từ tiếp nhận đến trả máy.
            </p>

            {/* Trust items */}
            <ul className="mt-5 flex flex-wrap gap-x-5 gap-y-2">
              {trustItems.map((item) => (
                <li key={item} className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <CheckCircle2
                    aria-hidden="true"
                    className="size-4 text-primary shrink-0"
                  />
                  {item}
                </li>
              ))}
            </ul>

            {/* CTAs */}
            <div className="mt-8 flex flex-wrap gap-3">
              <Button
                asChild
                size="lg"
                className="btn-primary-glow rounded-xl px-6 font-semibold"
              >
                <Link to="/booking">
                  <CalendarClock aria-hidden="true" className="size-4" />
                  Đặt lịch ngay
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="rounded-xl px-6 font-semibold border-border hover:border-primary/40 hover:bg-primary/5 hover:text-primary transition-all duration-200"
              >
                <Link to="/services">
                  Xem dịch vụ
                  <ArrowRight aria-hidden="true" className="size-4" />
                </Link>
              </Button>
            </div>

            {/* Social proof */}
            <div className="mt-8 flex items-center gap-3 text-sm">
              <div className="flex -space-x-2">
                {["TH", "NK", "LM"].map((initials, i) => (
                  <div
                    key={initials}
                    aria-hidden="true"
                    className="flex size-8 items-center justify-center rounded-full border-2 border-white text-xs font-semibold text-white"
                    style={{ background: ["#6366F1", "#8B5CF6", "#A78BFA"][i] }}
                  >
                    {initials}
                  </div>
                ))}
              </div>
              <div>
                <div className="flex gap-0.5" aria-hidden="true">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star key={i} className="size-3.5 fill-amber-400 text-amber-400" />
                  ))}
                </div>
                <p className="text-muted-foreground mt-0.5">
                  <strong className="text-foreground font-semibold">4.9/5</strong> từ 500+ khách hàng
                </p>
              </div>
            </div>
          </div>

          {/* Right — Phone mockup card */}
          <PhoneMockup />
        </div>
      </div>
    </section>
  )
}

function PhoneMockup() {
  return (
    <aside
      aria-label="Minh họa ứng dụng đặt lịch sửa chữa điện thoại"
      className="relative mx-auto w-full max-w-[480px]"
    >
      {/* Glow behind card */}
      <div
        aria-hidden="true"
        className="absolute inset-8 -z-10 rounded-3xl bg-primary/20 blur-3xl"
      />

      {/* Main app card */}
      <div className="overflow-hidden rounded-3xl border border-border bg-white shadow-2xl shadow-primary/10">
        {/* App header bar */}
        <div className="flex items-center justify-between border-b bg-white px-5 py-3.5">
          <div className="flex items-center gap-2">
            <div className="grid size-7 place-items-center rounded-lg bg-primary">
              <Smartphone aria-hidden="true" className="size-3.5 text-white" />
            </div>
            <span className="text-sm font-bold text-foreground">FixPhone</span>
          </div>
          <div className="flex items-center gap-1">
            {["#EF4444", "#F59E0B", "#10B981"].map((color, i) => (
              <div
                key={i}
                aria-hidden="true"
                className="size-2.5 rounded-full"
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
        </div>

        {/* Hero content in mockup */}
        <div className="bg-gradient-to-br from-primary/8 via-violet-500/5 to-transparent px-5 py-6">
          <p className="text-lg font-bold leading-snug text-foreground">
            Sửa điện thoại nhanh,
            <br />
            <span className="gradient-text-hero">đặt lịch chỉ 1 phút</span>
          </p>
          <p className="mt-1.5 text-xs text-muted-foreground">
            Chọn dịch vụ, chọn ngày giờ phù hợp và nhận thông báo tức thì.
          </p>

          {/* Search bar mockup */}
          <div className="mt-4 flex items-center gap-2 rounded-xl border bg-white px-3 py-2.5 text-sm text-muted-foreground shadow-sm">
            <span className="size-4 rounded bg-primary/15 flex items-center justify-center">
              <Zap aria-hidden="true" className="size-2.5 text-primary" />
            </span>
            Tìm kiếm dịch vụ sửa chữa...
            <span className="ml-auto rounded-lg bg-primary px-2.5 py-1 text-xs font-semibold text-white">
              Tìm
            </span>
          </div>
        </div>

        {/* Services grid */}
        <div className="px-5 pb-5">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Dịch vụ phổ biến
          </p>
          <div className="grid grid-cols-2 gap-2">
            {quickServices.map(({ icon: Icon, label, price }) => (
              <button
                key={label}
                type="button"
                className="group flex items-start gap-3 rounded-xl border bg-background p-3 text-left transition-all duration-150 hover:border-primary/40 hover:bg-primary/5 hover:shadow-sm"
              >
                <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary group-hover:bg-primary group-hover:text-white transition-all duration-150">
                  <Icon aria-hidden="true" className="size-4" />
                </span>
                <span>
                  <span className="block text-xs font-semibold text-foreground leading-tight">
                    {label}
                  </span>
                  <span className="block text-xs text-primary font-medium mt-0.5">
                    {price}
                  </span>
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Floating notification */}
      <div
        aria-hidden="true"
        className="absolute -bottom-3 -left-4 flex items-center gap-2.5 rounded-2xl border bg-white px-3.5 py-2.5 shadow-lg hidden sm:flex animate-float"
      >
        <div className="grid size-8 place-items-center rounded-xl bg-emerald-500/15">
          <CheckCircle2 className="size-4 text-emerald-600" />
        </div>
        <div>
          <p className="text-xs font-semibold text-foreground">Đặt lịch thành công!</p>
          <p className="text-xs text-muted-foreground">iPhone 13 — Thay pin — 09:00</p>
        </div>
      </div>
    </aside>
  )
}
