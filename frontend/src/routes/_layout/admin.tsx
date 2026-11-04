import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, isRedirect, redirect } from "@tanstack/react-router"
import { Suspense } from "react"

import { type UserPublic, UsersService } from "@/client"
import AddUser from "@/components/Admin/AddUser"
import { columns, type UserTableData } from "@/components/Admin/columns"
import { DataTable } from "@/components/Common/DataTable"
import PendingUsers from "@/components/Pending/PendingUsers"
import useAuth from "@/hooks/useAuth"
import { APP_NAME, pageHead } from "@/lib/seo"

function getUsersQueryOptions() {
  return {
    queryFn: async () =>
      (
        await UsersService.readUsers({
          query: { skip: 0, limit: 100 },
          throwOnError: true,
        })
      ).data,
    queryKey: ["users"],
  }
}

export const Route = createFileRoute("/_layout/admin")({
  component: Admin,
  beforeLoad: async () => {
    try {
      const { data: user } = await UsersService.readUserMe()
      if (!user.is_superuser) {
        throw redirect({
          to: "/app",
        })
      }
    } catch (error) {
      if (isRedirect(error)) throw error
      localStorage.removeItem("access_token")
      localStorage.removeItem("refresh_token")
      throw redirect({ to: "/login" })
    }
  },
  head: pageHead("Quản trị tài khoản"),
})

function UsersTableContent() {
  const { user: currentUser } = useAuth()
  const { data: users } = useSuspenseQuery(getUsersQueryOptions())

  const tableData: UserTableData[] = users.data.map((user: UserPublic) => ({
    ...user,
    isCurrentUser: currentUser?.id === user.id,
  }))

  return <DataTable columns={columns} data={tableData} />
}

function UsersTable() {
  return (
    <Suspense fallback={<PendingUsers />}>
      <UsersTableContent />
    </Suspense>
  )
}

function Admin() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Quản trị tài khoản
          </h1>
          <p className="text-muted-foreground">
            Quản lý tài khoản, trạng thái hoạt động và vai trò trong {APP_NAME}
          </p>
        </div>
        <AddUser />
      </div>
      <UsersTable />
    </div>
  )
}
