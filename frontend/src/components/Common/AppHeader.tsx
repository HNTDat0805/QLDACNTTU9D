import { SidebarTrigger } from "@/components/ui/sidebar"

export function AppHeader() {
  return (
    <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-3 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 sm:px-6">
      <SidebarTrigger
        className="-ml-1 text-muted-foreground"
        aria-label="Mở hoặc đóng thanh điều hướng"
      />
      <p className="text-sm font-medium text-muted-foreground">
        Khu vực làm việc
      </p>
    </header>
  )
}
