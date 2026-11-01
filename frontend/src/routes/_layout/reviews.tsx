import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { AppointmentsService, CommerceService } from "@/client"
import {
  ActionForm,
  DataState,
  PageTitle,
  Panel,
} from "@/components/Operations/shared"
export const Route = createFileRoute("/_layout/reviews")({ component: Reviews })
function Reviews() {
  const appointments = useQuery({
    queryKey: ["my-appointments", "reviewable"],
    queryFn: async () =>
      (await AppointmentsService.readMyAppointments({ query: { limit: 100 } }))
        .data,
  })
  const reviews = useQuery({
    queryKey: ["operations", "reviews"],
    queryFn: async () =>
      (await CommerceService.readMyReviews({ query: { limit: 100 } })).data,
  })
  const reviewed = new Set(reviews.data?.data.map((r) => r.appointment_id))
  return (
    <section className="max-w-3xl space-y-6">
      <PageTitle
        title="Đánh giá dịch vụ"
        description="Chia sẻ trải nghiệm sau khi hoàn tất sửa chữa."
      />
      <DataState
        pending={appointments.isPending || reviews.isPending}
        error={appointments.error || reviews.error}
      >
        <Panel title="Gửi đánh giá">
          <ActionForm
            fields={[
              {
                name: "appointment",
                label: "Lịch hẹn đã hoàn tất",
                required: true,
                options:
                  appointments.data?.data
                    .filter(
                      (a) => a.status === "COMPLETED" && !reviewed.has(a.id),
                    )
                    .map((a) => ({
                      value: a.id,
                      label: a.appointment_number,
                    })) ?? [],
              },
              {
                name: "rating",
                label: "Số sao",
                required: true,
                options: [5, 4, 3, 2, 1].map((value) => ({
                  value: String(value),
                  label: `${value} sao`,
                })),
              },
              { name: "comment", label: "Nhận xét" },
            ]}
            submitLabel="Gửi đánh giá"
            onSubmit={(v) =>
              CommerceService.submitReview({
                body: {
                  appointment_id: v.appointment,
                  rating: Number(v.rating),
                  comment: v.comment || null,
                },
              })
            }
          />
        </Panel>
        {reviews.data?.data.map((r) => (
          <Panel key={r.id} title={`${r.rating}/5 sao`}>
            <p>{r.comment || "Không có nhận xét thêm"}</p>
          </Panel>
        ))}
      </DataState>
    </section>
  )
}
