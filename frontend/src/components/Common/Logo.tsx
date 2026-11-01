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
    <span className={cn("inline-flex items-center gap-2", className)}>
      <span className="rounded-md bg-primary p-1 text-primary-foreground">
        <Smartphone aria-hidden="true" className="size-4" />
      </span>
      {variant !== "icon" && (
        <span
          className={cn(
            "text-lg font-bold tracking-tight",
            variant === "responsive" && "group-data-[collapsible=icon]:hidden",
          )}
        >
          FixCare
        </span>
      )}
    </span>
  )

  if (!asLink) {
    return content
  }

  return (
    <Link to="/" aria-label="FixCare - Trang chủ">
      {content}
    </Link>
  )
}
