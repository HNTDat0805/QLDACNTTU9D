import { Link } from "@tanstack/react-router"

import { Appearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import { Button } from "@/components/ui/button"

export function PublicHeader() {
  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <nav
        aria-label="Điều hướng công khai"
        className="mx-auto flex min-h-16 max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8"
      >
        <Logo />
        <div className="flex flex-wrap items-center gap-2">
          <Button asChild size="sm" variant="ghost">
            <Link to="/services">Dịch vụ</Link>
          </Button>
          <Button asChild size="sm" variant="ghost">
            <Link to="/booking">Đặt lịch sửa chữa</Link>
          </Button>
          <Appearance />
          <Button asChild size="sm" variant="ghost">
            <Link to="/about">Giới thiệu</Link>
          </Button>
          <Button asChild size="sm" variant="ghost">
            <Link to="/login">Đăng nhập</Link>
          </Button>
          <Button asChild size="sm">
            <Link to="/signup">Tạo tài khoản</Link>
          </Button>
        </div>
      </nav>
    </header>
  )
}
