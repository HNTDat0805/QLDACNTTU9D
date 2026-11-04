import { Link } from "@tanstack/react-router"
import { Smartphone } from "lucide-react"

import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "full" | "icon" | "responsive"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const content = (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <span className="flex size-8 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-xs">
        <Smartphone aria-hidden="true" className="size-4" />
      </span>
      {variant !== "icon" && (
        <span
          className={cn(
            "text-lg font-bold tracking-tight text-foreground",
            variant === "responsive" && "group-data-[collapsible=icon]:hidden",
          )}
        >
          FixPhone
        </span>
      )}
    </span>
  )

  if (!asLink) {
    return content
  }

  return (
    <Link to="/" aria-label="FixPhone - Trang chủ">
      {content}
    </Link>
  )
}
