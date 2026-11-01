import type { ReactNode } from "react"

import { Footer } from "@/components/Common/Footer"
import { PublicHeader } from "@/components/Common/PublicHeader"

interface PublicLayoutProps {
  children: ReactNode
}

export function PublicLayout({ children }: PublicLayoutProps) {
  return (
    <div className="flex min-h-svh flex-col bg-background">
      <PublicHeader />
      <main id="main-content" className="flex-1">
        {children}
      </main>
      <Footer />
    </div>
  )
}
