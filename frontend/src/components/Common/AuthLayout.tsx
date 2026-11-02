import { CalendarClock, ClipboardCheck, Smartphone } from "lucide-react"

import { Appearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import { Footer } from "./Footer"

interface AuthLayoutProps {
  children: React.ReactNode
}

const features = [
  {
    icon: CalendarClock,
    text: "Đặt lịch sửa chữa chỉ trong 1 phút",
  },
  {
    icon: Smartphone,
    text: "Theo dõi thiết bị theo thời gian thực",
  },
  {
    icon: ClipboardCheck,
    text: "Quy trình minh bạch từ tiếp nhận đến trả máy",
  },
]

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      {/* Left — Indigo panel theo Figma */}
      <div className="relative hidden overflow-hidden lg:flex lg:flex-col lg:justify-between bg-gradient-to-br from-primary via-violet-600 to-purple-700 p-10 text-white">
        {/* Decoration */}
        <div aria-hidden="true" className="pointer-events-none absolute inset-0">
          <div className="absolute -top-40 -right-40 h-96 w-96 rounded-full bg-white/8 blur-3xl" />
          <div className="absolute bottom-0 left-0 h-72 w-72 rounded-full bg-violet-900/40 blur-3xl" />
          <div
            className="absolute inset-0 opacity-[0.05]"
            style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='2' cy='2' r='1.5' fill='white'/%3E%3C/svg%3E")`,
              backgroundSize: "40px 40px",
            }}
          />
        </div>

        {/* Logo */}
        <div className="relative flex items-center gap-2">
          <div className="grid size-8 place-items-center rounded-xl bg-white/20">
            <Smartphone className="size-4" aria-hidden="true" />
          </div>
          <span className="text-lg font-bold tracking-tight">FixPhone</span>
        </div>

        {/* Center content */}
        <div className="relative space-y-8">
          <div>
            <h2 className="text-3xl font-bold tracking-tight leading-snug text-balance">
              Chào mừng trở lại!
            </h2>
            <p className="mt-3 text-base text-white/75 leading-relaxed max-w-xs">
              Đăng nhập để quản lý lịch hẹn, theo dõi thiết bị và nhận thông báo tức thì.
            </p>
          </div>

          <ul className="space-y-4">
            {features.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3">
                <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-white/15 backdrop-blur-sm">
                  <Icon aria-hidden="true" className="size-5" />
                </span>
                <span className="text-sm font-medium text-white/90 leading-snug">{text}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Rating at bottom */}
        <div className="relative">
          <div className="flex items-center gap-1 mb-1.5" aria-label="Đánh giá 4.9 trên 5 sao">
            {Array.from({ length: 5 }).map((_, i) => (
              <svg key={i} className="size-4 fill-amber-400 text-amber-400" viewBox="0 0 20 20" aria-hidden="true">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            ))}
          </div>
          <p className="text-sm text-white/75">
            <strong className="text-white font-semibold">4.9/5</strong> — Được tin dùng bởi 500+ khách hàng
          </p>
        </div>
      </div>

      {/* Right — Form panel */}
      <div className="flex flex-col gap-4 p-6 md:p-10 bg-background">
        <div className="flex items-center justify-between">
          <div className="lg:hidden">
            <Logo />
          </div>
          <div className="lg:ml-auto">
            <Appearance />
          </div>
        </div>
        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-sm">{children}</div>
        </div>
        <Footer />
      </div>
    </div>
  )
}
