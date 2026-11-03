import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { AlertCircle, CheckCircle2, Send, Sparkles, Star } from "lucide-react"
import { useState } from "react"

import { AppointmentsService, CommerceService } from "@/client"
import { DataState, PageTitle, Panel } from "@/components/Operations/shared"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import useCustomToast from "@/hooks/useCustomToast"
import { pageHead } from "@/lib/seo"
import { cn } from "@/lib/utils"
import { getApiErrorMessage } from "@/utils"

export const Route = createFileRoute("/_layout/reviews")({
  component: Reviews,
  head: pageHead("Đánh giá dịch vụ"),
})

const STAR_LABELS: Record<number, string> = {
  1: "Rất tệ",
  2: "Chưa hài lòng",
  3: "Bình thường",
  4: "Hài lòng",
  5: "Tuyệt vời",
}

function StarRatingPicker({
  value,
  onChange,
}: {
  value: number
  onChange: (val: number) => void
}) {
  const [hovered, setHovered] = useState<number | null>(null)
  const activeRating = hovered ?? value

  return (
    <div className="space-y-2">
      {/* 5 Ngôi sao tương tác chuẩn CH Play kèm dropdown đồng bộ */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1">
          {[1, 2, 3, 4, 5].map((star) => {
            const isFilled = star <= activeRating
            return (
              <button
                key={star}
                type="button"
                aria-pressed={value >= star}
                aria-label={`${star} sao`}
                onClick={() => onChange(star)}
                onMouseEnter={() => setHovered(star)}
                onMouseLeave={() => setHovered(null)}
                className="group relative flex size-9 sm:size-10 items-center justify-center rounded-xl p-1 transition-all duration-150 hover:bg-amber-50 dark:hover:bg-amber-950/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 cursor-pointer"
              >
                <Star
                  className={cn(
                    "size-6 sm:size-7 transition-all duration-150 group-hover:scale-115",
                    isFilled
                      ? "fill-amber-400 text-amber-500 drop-shadow-xs"
                      : "fill-transparent text-muted-foreground/30 group-hover:text-amber-300",
                  )}
                />
              </button>
            )
          })}
        </div>

        {/* Dropdown số sao đồng bộ hai chiều */}
        <select
          id="rating"
          name="rating"
          aria-label="Số sao"
          value={String(value)}
          onChange={(e) => onChange(Number(e.target.value))}
          className="h-9 rounded-lg border border-input bg-background px-3 py-1 text-xs font-semibold text-foreground shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring cursor-pointer"
        >
          {[5, 4, 3, 2, 1].map((n) => (
            <option key={n} value={String(n)}>
              {n} sao ({STAR_LABELS[n]})
            </option>
          ))}
        </select>
      </div>

      {/* Nhãn mô tả cảm xúc tương ứng số sao */}
      <div className="flex items-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-600 dark:text-amber-400">
          <Sparkles className="size-3.5" />
          {value} / 5 sao · {STAR_LABELS[value] || "Chưa chọn"}
        </span>
        {hovered && hovered !== value && (
          <span className="text-xs text-muted-foreground">
            (Xem trước: {hovered} sao - {STAR_LABELS[hovered]})
          </span>
        )}
      </div>
    </div>
  )
}

interface ReviewFormProps {
  appointments: Array<{
    id: string
    appointment_number: string
    services?: Array<{ service_name: string }>
    device?: { brand: string; model: string } | null
  }>
  onSubmit: (data: {
    appointment_id: string
    rating: number
    comment?: string | null
  }) => void
  isPending: boolean
}

function ReviewForm({ appointments, onSubmit, isPending }: ReviewFormProps) {
  const [appointmentId, setAppointmentId] = useState(appointments[0]?.id ?? "")
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState("")
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!appointmentId) {
      setError("Vui lòng chọn lịch hẹn đã hoàn tất để gửi đánh giá.")
      return
    }
    setError(null)
    onSubmit({
      appointment_id: appointmentId,
      rating,
      comment: comment.trim() || null,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Chọn lịch hẹn đã hoàn tất */}
      <div className="space-y-1.5">
        <Label htmlFor="appointment" className="text-sm font-semibold">
          Lịch hẹn đã hoàn tất <span className="text-destructive">*</span>
        </Label>
        <select
          id="appointment"
          name="appointment"
          aria-label="Lịch hẹn đã hoàn tất"
          value={appointmentId}
          onChange={(e) => {
            setAppointmentId(e.target.value)
            if (error) setError(null)
          }}
          className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {appointments.length > 1 && (
            <option value="">-- Chọn lịch hẹn đã hoàn tất --</option>
          )}
          {appointments.map((a) => {
            const extra = [
              a.services?.[0]?.service_name,
              a.device ? `${a.device.brand} ${a.device.model}` : null,
            ]
              .filter(Boolean)
              .join(" - ")
            return (
              <option key={a.id} value={a.id}>
                {extra
                  ? `${a.appointment_number} · ${extra}`
                  : a.appointment_number}
              </option>
            )
          })}
        </select>
      </div>

      {/* 5 Ngôi sao chuẩn CH Play */}
      <div className="space-y-1.5">
        <Label className="text-sm font-semibold">
          Đánh giá số sao <span className="text-destructive">*</span>
        </Label>
        <p className="text-xs text-muted-foreground">
          Chạm hoặc chọn vào số ngôi sao tương ứng với độ hài lòng của bạn (1 -
          5 sao).
        </p>
        <StarRatingPicker value={rating} onChange={setRating} />
      </div>

      {/* Nhận xét */}
      <div className="space-y-1.5">
        <Label htmlFor="comment" className="text-sm font-semibold">
          Nhận xét
        </Label>
        <textarea
          id="comment"
          name="comment"
          aria-label="Nhận xét"
          rows={3}
          placeholder="Chia sẻ trải nghiệm của bạn về dịch vụ, kỹ thuật viên hoặc thiết bị sau khi nhận lại máy..."
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          className="w-full rounded-lg border border-input bg-background p-3 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-y"
        />
      </div>

      {error && (
        <p
          role="alert"
          className="text-xs text-destructive font-medium flex items-center gap-1.5"
        >
          <AlertCircle className="size-4 shrink-0" />
          {error}
        </p>
      )}

      <Button
        type="submit"
        disabled={isPending}
        className="btn-primary-glow font-medium cursor-pointer"
      >
        <Send className="size-4 mr-1.5" />
        {isPending ? "Đang gửi đánh giá..." : "Gửi đánh giá"}
      </Button>
    </form>
  )
}

function Reviews() {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

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

  const submitReview = useMutation({
    mutationFn: async (data: {
      appointment_id: string
      rating: number
      comment?: string | null
    }) => {
      return (await CommerceService.submitReview({ body: data })).data
    },
    onSuccess: () => {
      showSuccessToast("Cảm ơn bạn! Đánh giá đã được ghi nhận thành công.")
      queryClient.invalidateQueries({ queryKey: ["operations", "reviews"] })
      queryClient.invalidateQueries({ queryKey: ["my-appointments"] })
    },
    onError: (err) => {
      showErrorToast(getApiErrorMessage(err))
    },
  })

  const reviewed = new Set(reviews.data?.data.map((r) => r.appointment_id))
  const unreviewedAppointments =
    appointments.data?.data.filter(
      (a) => a.status === "COMPLETED" && !reviewed.has(a.id),
    ) ?? []

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
          {unreviewedAppointments.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed px-4 py-8 text-center">
              <CheckCircle2 className="size-10 text-emerald-500" />
              <p className="mt-3 font-semibold text-foreground">
                Bạn không có lịch hẹn hoàn tất nào chưa được đánh giá
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Tất cả các đợt sửa chữa hoàn tất của bạn đều đã được đánh giá,
                hoặc bạn chưa có lịch hẹn nào hoàn tất.
              </p>
            </div>
          ) : (
            <ReviewForm
              appointments={unreviewedAppointments}
              onSubmit={(v) => submitReview.mutate(v)}
              isPending={submitReview.isPending}
            />
          )}
        </Panel>

        <div className="space-y-4">
          <h2 className="text-base font-semibold text-foreground">
            Lịch sử đánh giá của bạn ({reviews.data?.data.length ?? 0})
          </h2>
          {reviews.data?.data.map((r) => (
            <Panel key={r.id} title={`${r.rating}/5 sao`}>
              <div className="space-y-1.5">
                <div className="flex items-center gap-1 text-amber-500">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star
                      key={i}
                      className={`size-4 ${
                        i < r.rating
                          ? "fill-amber-400 text-amber-500"
                          : "fill-transparent text-muted-foreground/30"
                      }`}
                    />
                  ))}
                  <span className="ml-1.5 text-xs font-semibold text-muted-foreground">
                    {STAR_LABELS[r.rating]}
                  </span>
                </div>
                <p className="text-sm text-foreground">
                  {r.comment || "Không có nhận xét thêm"}
                </p>
              </div>
            </Panel>
          ))}
          {reviews.data?.data.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Bạn chưa gửi đánh giá nào.
            </p>
          )}
        </div>
      </DataState>
    </section>
  )
}
