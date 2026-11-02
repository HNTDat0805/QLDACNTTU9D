import { Link } from "@tanstack/react-router"

import { Appearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import { Button } from "@/components/ui/button"

export function PublicHeader() {
  return (
    <header className="sticky top-0 z-50 border-b bg-white/90 backdrop-blur-xl supports-[backdrop-filter]:bg-white/80">
      <nav
        aria-label="Điều hướng công khai"
        className="mx-auto flex min-h-[60px] max-w-7xl items-center justify-between gap-4 px-4 py-2.5 sm:px-6 lg:px-8"
      >
        <Logo />

        {/* Nav links */}
        <div className="hidden items-center gap-1 md:flex">
          {[
            { to: "/", label: "Trang chủ" },
            { to: "/services", label: "Dịch vụ" },
            { to: "/booking", label: "Đặt lịch" },
            { to: "/about", label: "Giới thiệu" },
          ].map(({ to, label }) => (
            <Button
              key={to}
              asChild
              size="sm"
              variant="ghost"
              className="text-muted-foreground hover:text-foreground hover:bg-primary/8 rounded-lg font-medium transition-all duration-150"
            >
              <Link to={to}>{label}</Link>
            </Button>
          ))}
        </div>

        {/* Right side */}
        <div className="flex items-center gap-2">
          <Appearance />
          <div className="h-5 w-px bg-border mx-1" aria-hidden="true" />
          <Button
            asChild
            size="sm"
            variant="ghost"
            className="font-medium text-muted-foreground hover:text-foreground"
          >
            <Link to="/login">Đăng nhập</Link>
          </Button>
          <Button
            asChild
            size="sm"
            className="rounded-lg font-semibold btn-primary-glow"
          >
            <Link to="/booking">Đặt lịch</Link>
          </Button>
        </div>
      </nav>
    </header>
  )
}
