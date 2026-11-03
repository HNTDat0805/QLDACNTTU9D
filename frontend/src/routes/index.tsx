import { createFileRoute } from "@tanstack/react-router"

import { PublicLayout } from "@/components/Common/PublicLayout"
import { LandingAudience } from "@/components/landing/LandingAudience"
import { LandingCta } from "@/components/landing/LandingCta"
import { LandingFeatures } from "@/components/landing/LandingFeatures"
import { LandingHero } from "@/components/landing/LandingHero"
import { LandingWorkflow } from "@/components/landing/LandingWorkflow"
import { APP_DESCRIPTION, pageHead } from "@/lib/seo"

export const Route = createFileRoute("/")({
  component: PublicHome,
  head: pageHead(undefined, APP_DESCRIPTION),
})

function PublicHome() {
  return (
    <PublicLayout>
      <LandingHero />
      <LandingFeatures />
      <LandingWorkflow />
      <LandingAudience />
      <LandingCta />
    </PublicLayout>
  )
}
