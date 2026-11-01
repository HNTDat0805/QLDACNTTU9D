import { createFileRoute } from "@tanstack/react-router"

import { PublicLayout } from "@/components/Common/PublicLayout"
import { LandingAudience } from "@/components/landing/LandingAudience"
import { LandingCta } from "@/components/landing/LandingCta"
import { LandingFeatures } from "@/components/landing/LandingFeatures"
import { LandingHero } from "@/components/landing/LandingHero"
import { LandingWorkflow } from "@/components/landing/LandingWorkflow"

export const Route = createFileRoute("/")({
  component: PublicHome,
  head: () => ({
    meta: [
      { title: "FixCare | Quản lý sửa chữa điện thoại minh bạch" },
      {
        name: "description",
        content:
          "FixCare là hệ thống hỗ trợ tổ chức lịch hẹn, tiếp nhận thiết bị và theo dõi quy trình sửa chữa điện thoại.",
      },
    ],
  }),
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
