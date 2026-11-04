import {
  createFileRoute,
  isRedirect,
  Outlet,
  redirect,
} from "@tanstack/react-router"
import { UsersService } from "@/client"

export const Route = createFileRoute("/_layout/workspace")({
  beforeLoad: async () => {
    try {
      const { data: user } = await UsersService.readUserMe()
      if (
        !user.is_superuser &&
        !["admin", "manager", "staff", "technician"].includes(user.role ?? "")
      )
        throw redirect({ to: "/app" })
    } catch (error) {
      if (isRedirect(error)) throw error
      localStorage.removeItem("access_token")
      localStorage.removeItem("refresh_token")
      throw redirect({ to: "/login" })
    }
  },
  component: Outlet,
})
