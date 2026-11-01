import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
import { UsersService } from "@/client"

export const Route = createFileRoute("/_layout/workspace")({
  beforeLoad: async () => {
    const { data: user } = await UsersService.readUserMe()
    if (
      !user.is_superuser &&
      !["admin", "manager", "staff", "technician"].includes(user.role ?? "")
    )
      throw redirect({ to: "/app" })
  },
  component: Outlet,
})
