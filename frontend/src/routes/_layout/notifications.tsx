import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { CommerceService } from "@/client"
import {
  ActionForm,
  DataState,
  dateTime,
  Pager,
  PageTitle,
  Panel,
} from "@/components/Operations/shared"
export const Route = createFileRoute("/_layout/notifications")({
  component: Notifications,
})
function Notifications() {
  const [page, setPage] = useState(0)
  const list = useQuery({
    queryKey: ["operations", "notifications", page],
    queryFn: async () =>
      (
        await CommerceService.readNotifications({
          query: { skip: page * 20, limit: 20 },
        })
      ).data,
  })
  return (
    <section className="space-y-4">
      <PageTitle
        title="Thông báo"
        description={`${list.data?.unread_count ?? 0} thông báo chưa đọc`}
      />
      <DataState
        pending={list.isPending}
        error={list.error}
        empty={!list.data?.count}
      >
        {list.data?.data.map((n) => (
          <Panel key={n.id} title={n.title}>
            <p>{n.message}</p>
            <p className="my-3 text-sm text-muted-foreground">
              {dateTime(n.created_at)}
            </p>
            {!n.is_read && (
              <ActionForm
                fields={[]}
                submitLabel="Đánh dấu đã đọc"
                onSubmit={() =>
                  CommerceService.markNotificationRead({
                    path: { notification_id: n.id },
                  })
                }
              />
            )}
          </Panel>
        ))}
      </DataState>
      <Pager page={page} count={list.data?.count ?? 0} setPage={setPage} />
    </section>
  )
}
