import { Link } from "@tanstack/react-router"
import { Home, LayoutDashboard, LogOut, Settings } from "lucide-react"

import { getRoleLabel } from "@/components/Sidebar/roles"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import useAuth from "@/hooks/useAuth"
import { cn } from "@/lib/utils"
import { getInitials } from "@/utils"

export function getAvatarTone(
  role?: string | null,
  isSuperuser?: boolean,
): string {
  if (isSuperuser || role === "admin") {
    return "bg-indigo-600 text-white"
  }
  if (role === "manager") {
    return "bg-amber-500 text-white"
  }
  if (role === "staff" || role === "technician") {
    return "bg-sky-500 text-white"
  }
  return "bg-pink-500 text-white"
}

interface UserMenuProps {
  showOverviewLink?: boolean
  className?: string
}

export function UserMenu({
  showOverviewLink = true,
  className,
}: UserMenuProps) {
  const { user, logout } = useAuth()

  const displayName = user?.full_name || user?.email || "Tài khoản"
  const roleLabel = getRoleLabel(user?.role ?? undefined, user?.is_superuser)
  const isCustomer =
    !user?.is_superuser && (user?.role ?? "customer") === "customer"

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          data-testid="user-menu"
          aria-label="Tài khoản người dùng"
          className={cn(
            "inline-flex items-center gap-2.5 rounded-full border border-transparent py-1 pl-2.5 pr-1.5 text-left transition-colors hover:border-border hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            className,
          )}
        >
          <span className="hidden max-w-[150px] flex-col text-right leading-tight sm:flex">
            <span className="truncate text-xs font-semibold text-foreground">
              {displayName}
            </span>
            <span className="truncate text-[11px] text-muted-foreground">
              {roleLabel}
            </span>
          </span>
          <span
            aria-hidden="true"
            className={cn(
              "flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-bold shadow-xs",
              getAvatarTone(user?.role, user?.is_superuser),
            )}
          >
            {getInitials(user?.full_name || user?.email || "FP")}
          </span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        sideOffset={8}
        className="w-60 rounded-xl"
      >
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col gap-0.5">
            <p className="truncate text-sm font-semibold text-foreground">
              {displayName}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {user?.email}
            </p>
            <span className="inline-block mt-0.5 text-[11px] font-medium text-primary">
              {roleLabel}
            </span>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {showOverviewLink && !isCustomer && (
          <DropdownMenuItem asChild>
            <Link to="/app" className="cursor-pointer">
              <LayoutDashboard aria-hidden="true" className="size-4" />
              Tổng quan
            </Link>
          </DropdownMenuItem>
        )}
        {showOverviewLink && isCustomer && (
          <DropdownMenuItem asChild>
            <Link to="/" className="cursor-pointer">
              <Home aria-hidden="true" className="size-4" />
              Trang chủ
            </Link>
          </DropdownMenuItem>
        )}
        <DropdownMenuItem asChild>
          <Link to="/settings" className="cursor-pointer">
            <Settings aria-hidden="true" className="size-4" />
            Cài đặt tài khoản
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={logout}
          className="cursor-pointer text-destructive focus:text-destructive"
        >
          <LogOut aria-hidden="true" className="size-4" />
          Đăng xuất
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
