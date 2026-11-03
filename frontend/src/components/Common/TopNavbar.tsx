import { useQuery } from "@tanstack/react-query"
import { Link, useRouterState } from "@tanstack/react-router"
import { Bell, LogOut, Menu, Settings, Smartphone, X } from "lucide-react"
import { useState } from "react"

import { CommerceService } from "@/client"
import { Appearance } from "@/components/Common/Appearance"
import { getAvatarTone, UserMenu } from "@/components/Common/UserMenu"
import { Button } from "@/components/ui/button"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import {
  getBrandDestination,
  getNavItemsForUser,
  getUserRoleLabel,
  type NavItem,
} from "@/lib/navigation"
import { cn } from "@/lib/utils"
import { getInitials } from "@/utils"

export function TopNavbar() {
  const loggedIn = isLoggedIn()
  const { user, logout } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  })

  const notifications = useQuery({
    queryKey: ["operations", "notifications", "badge", user?.id],
    enabled: Boolean(loggedIn && user?.id),
    retry: false,
    meta: { silent: true },
    queryFn: async () =>
      (
        await CommerceService.readNotifications({
          query: { skip: 0, limit: 1 },
        })
      ).data,
  })

  const navItems = getNavItemsForUser(user, loggedIn)
  const roleLabel = getUserRoleLabel(user, loggedIn)
  const displayName = user?.full_name || user?.email || "Tài khoản"
  const brandDestination = getBrandDestination(user, loggedIn)
  const unreadCount = notifications.data?.unread_count ?? 0

  const isPublicRoute =
    pathname === "/" ||
    pathname.startsWith("/services") ||
    pathname.startsWith("/booking") ||
    pathname.startsWith("/about")

  const navAriaLabel =
    !loggedIn || isPublicRoute ? "Điều hướng công khai" : "Điều hướng chính"

  const isItemActive = (item: NavItem) => {
    if (item.exact) {
      return pathname === item.path
    }
    return pathname === item.path || pathname.startsWith(`${item.path}/`)
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/80 bg-card/95 backdrop-blur-xl supports-[backdrop-filter]:bg-card/85 shadow-[0_1px_3px_rgba(15,23,42,0.04)]">
      <nav
        aria-label={navAriaLabel}
        className="mx-auto flex min-h-16 max-w-[1440px] items-center justify-between gap-3 px-4 sm:px-6 lg:px-8"
      >
        {/* Left: Mobile Toggle + Brand */}
        <div className="flex items-center gap-2.5">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="lg:hidden text-muted-foreground hover:text-foreground"
            aria-label="Mở hoặc đóng thanh điều hướng"
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen((prev) => !prev)}
          >
            {mobileOpen ? (
              <X aria-hidden="true" className="size-5" />
            ) : (
              <Menu aria-hidden="true" className="size-5" />
            )}
          </Button>

          <Link
            to={brandDestination}
            className="inline-flex items-center gap-2.5 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="FixPhone - Trang chủ"
          >
            <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
              <Smartphone aria-hidden="true" className="size-4" />
            </span>
            <span className="flex flex-col leading-tight">
              <span className="text-base font-bold tracking-tight text-foreground">
                FixPhone
              </span>
              {loggedIn && roleLabel && (
                <span className="text-[11px] font-medium text-muted-foreground">
                  {roleLabel}
                </span>
              )}
            </span>
          </Link>
        </div>

        {/* Center: Desktop Navigation Links (Synchronized by role) */}
        <div
          data-testid="desktop-nav"
          className="hidden lg:flex lg:flex-1 lg:items-center lg:justify-center lg:gap-0.5 lg:overflow-x-auto"
        >
          {navItems.map((item) => {
            const active = isItemActive(item)
            return (
              <Link
                key={item.path}
                to={item.path}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "relative inline-flex h-16 items-center whitespace-nowrap border-b-2 px-3 text-sm transition-colors",
                  active
                    ? "border-primary font-semibold text-primary"
                    : "border-transparent font-medium text-muted-foreground hover:border-border hover:text-foreground",
                )}
              >
                {item.title}
              </Link>
            )
          })}
        </div>

        {/* Right Controls */}
        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
          {loggedIn ? (
            <>
              {user?.role === "customer" && (
                <Button
                  asChild
                  size="sm"
                  className="btn-primary-glow hidden rounded-lg px-3 font-semibold sm:inline-flex"
                >
                  <Link to="/booking">Đặt lịch sửa chữa</Link>
                </Button>
              )}

              <Button
                asChild
                variant="ghost"
                size="icon"
                className={cn(
                  "relative rounded-full text-muted-foreground hover:text-foreground",
                  pathname === "/notifications" && "bg-primary/10 text-primary",
                )}
              >
                <Link to="/notifications" aria-label="Thông báo">
                  <Bell aria-hidden="true" className="size-4" />
                  {unreadCount > 0 && (
                    <span className="absolute -right-0.5 -top-0.5 flex min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold leading-4 text-white">
                      {unreadCount > 9 ? "9+" : unreadCount}
                    </span>
                  )}
                </Link>
              </Button>

              <Appearance />

              <div
                className="mx-0.5 hidden h-5 w-px bg-border sm:block"
                aria-hidden="true"
              />

              <UserMenu showOverviewLink={true} />
            </>
          ) : (
            <>
              <Appearance />

              <div
                className="mx-0.5 hidden h-5 w-px bg-border sm:block"
                aria-hidden="true"
              />

              <Button
                asChild
                size="sm"
                variant="ghost"
                className="px-2.5 font-medium text-muted-foreground hover:text-foreground sm:px-3"
              >
                <Link to="/login">Đăng nhập</Link>
              </Button>

              <Button
                asChild
                size="sm"
                variant="outline"
                className="hidden rounded-lg font-medium sm:inline-flex"
              >
                <Link to="/signup">Tạo tài khoản</Link>
              </Button>

              <Button
                asChild
                size="sm"
                className="btn-primary-glow hidden rounded-lg font-semibold sm:inline-flex"
              >
                <Link to="/booking">Đặt lịch sửa chữa</Link>
              </Button>
            </>
          )}
        </div>
      </nav>

      {/* Responsive Mobile Navigation Drawer */}
      {mobileOpen && (
        <nav
          aria-label="Điều hướng di động"
          className="border-t bg-card px-4 py-3 shadow-lg lg:hidden"
        >
          {loggedIn && (
            <div className="mb-3 flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2.5">
                <span
                  aria-hidden="true"
                  className={cn(
                    "flex size-9 shrink-0 items-center justify-center rounded-full text-xs font-bold shadow-xs",
                    getAvatarTone(user?.role, user?.is_superuser),
                  )}
                >
                  {getInitials(displayName)}
                </span>
                <div className="flex flex-col leading-tight">
                  <span className="text-sm font-semibold text-foreground">
                    {displayName}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {roleLabel}
                  </span>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setMobileOpen(false)
                  logout()
                }}
                className="text-destructive hover:text-destructive cursor-pointer"
              >
                <LogOut className="mr-1.5 size-4" />
                Đăng xuất
              </Button>
            </div>
          )}

          <div className="grid gap-1">
            {navItems.map((item) => {
              const active = isItemActive(item)
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  aria-current={active ? "page" : undefined}
                  onClick={() => setMobileOpen(false)}
                  className={cn(
                    "flex items-center justify-between rounded-lg px-3 py-2.5 text-sm transition-colors",
                    active
                      ? "bg-primary/10 font-semibold text-primary"
                      : "font-medium text-muted-foreground hover:bg-muted hover:text-foreground",
                  )}
                >
                  {item.title}
                </Link>
              )
            })}

            {loggedIn ? (
              <Link
                to="/settings"
                onClick={() => setMobileOpen(false)}
                className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <Settings className="size-4" />
                Cài đặt tài khoản
              </Link>
            ) : (
              <div className="mt-2 flex flex-col gap-2 border-t pt-2">
                <Link
                  to="/login"
                  onClick={() => setMobileOpen(false)}
                  className="flex items-center justify-center rounded-lg border py-2 text-sm font-medium hover:bg-muted"
                >
                  Đăng nhập
                </Link>
                <Link
                  to="/signup"
                  onClick={() => setMobileOpen(false)}
                  className="flex items-center justify-center rounded-lg bg-primary py-2 text-sm font-semibold text-primary-foreground"
                >
                  Tạo tài khoản
                </Link>
              </div>
            )}
          </div>
        </nav>
      )}
    </header>
  )
}
