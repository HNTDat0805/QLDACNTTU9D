import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { type ReactNode, useId, useRef, useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import { z } from "zod"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { getApiErrorMessage } from "@/utils"

export const states = [
  "PENDING",
  "CONFIRMED",
  "IN_PROGRESS",
  "COMPLETED",
  "CANCELLED",
] as const

export const statusLabels: Record<string, string> = {
  PENDING: "Chờ xác nhận",
  CONFIRMED: "Đã xác nhận",
  IN_PROGRESS: "Đang sửa",
  COMPLETED: "Hoàn tất",
  CANCELLED: "Đã hủy",
  DRAFT: "Nháp",
  SENT: "Đã gửi",
  ACCEPTED: "Đã duyệt",
  REJECTED: "Từ chối",
  PAID: "Đã thanh toán",
  UNPAID: "Chưa thanh toán",
  PARTIALLY_PAID: "Thanh toán một phần",
  AVAILABLE: "Sẵn sàng",
  OFF: "Nghỉ",
  BUSY: "Bận",
}

const statusTones: Record<string, string> = {
  PENDING:
    "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/15 dark:text-amber-300",
  SENT: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/15 dark:text-amber-300",
  PARTIALLY_PAID:
    "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/15 dark:text-amber-300",
  CONFIRMED:
    "border-indigo-200 bg-indigo-50 text-indigo-700 dark:border-indigo-500/30 dark:bg-indigo-500/15 dark:text-indigo-300",
  IN_PROGRESS:
    "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-500/30 dark:bg-sky-500/15 dark:text-sky-300",
  ACCEPTED:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/15 dark:text-emerald-300",
  COMPLETED:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/15 dark:text-emerald-300",
  PAID: "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/15 dark:text-emerald-300",
  AVAILABLE:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/15 dark:text-emerald-300",
  CANCELLED:
    "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/15 dark:text-rose-300",
  REJECTED:
    "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/15 dark:text-rose-300",
  UNPAID:
    "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/15 dark:text-rose-300",
  BUSY: "border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-500/30 dark:bg-orange-500/15 dark:text-orange-300",
}

export function Status({ value }: { value: string }) {
  const normalized = value?.toUpperCase?.() ?? value
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold",
        statusTones[normalized] ?? "border-border bg-muted/60 text-foreground",
      )}
    >
      {statusLabels[normalized] ?? statusLabels[value] ?? value}
    </span>
  )
}

export const money = (amount: number) =>
  new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" }).format(
    amount,
  )

export const dateTime = (date?: string | null) =>
  date ? new Date(date).toLocaleString("vi-VN") : "—"

export function PageTitle({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children?: ReactNode
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
          {title}
        </h1>
        {description && (
          <p className="mt-1.5 text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {children}
    </div>
  )
}

export function DataState({
  pending,
  error,
  empty,
  children,
}: {
  pending: boolean
  error: unknown
  empty?: boolean
  children: ReactNode
}) {
  if (pending)
    return (
      <div role="status" aria-label="Đang tải dữ liệu" className="space-y-3">
        <Skeleton className="h-24 w-full rounded-xl" />
        <Skeleton className="h-24 w-full rounded-xl" />
      </div>
    )
  if (error)
    return (
      <p
        role="alert"
        className="rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive"
      >
        {getApiErrorMessage(error)}
      </p>
    )
  if (empty)
    return (
      <div className="rounded-xl border border-dashed bg-card/60 p-10 text-center text-muted-foreground">
        Chưa có dữ liệu phù hợp. Hãy thử thay đổi bộ lọc.
      </div>
    )
  return children
}

export function Panel({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <Card className="border-border/80 shadow-xs">
      <CardHeader>
        <CardTitle className="text-lg">
          <h2>{title}</h2>
        </CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

export function Pager({
  page,
  count,
  setPage,
}: {
  page: number
  count: number
  setPage: (page: number) => void
}) {
  return (
    <div className="mt-4 flex items-center justify-between gap-3 text-sm">
      <span className="text-muted-foreground">
        {count} kết quả · Trang {page + 1}
      </span>
      <div className="flex gap-2">
        <Button
          variant="outline"
          disabled={!page}
          onClick={() => setPage(page - 1)}
        >
          Trước
        </Button>
        <Button
          variant="outline"
          disabled={(page + 1) * 20 >= count}
          onClick={() => setPage(page + 1)}
        >
          Sau
        </Button>
      </div>
    </div>
  )
}

export type FieldSpec = {
  name: string
  label: string
  type?:
    | "text"
    | "tel"
    | "email"
    | "number"
    | "date"
    | "time"
    | "datetime-local"
  required?: boolean
  min?: number
  max?: number
  options?: { value: string; label: string }[]
}

export function ActionForm({
  fields,
  submitLabel,
  onSubmit,
  initial = {},
  confirm = false,
}: {
  fields: FieldSpec[]
  submitLabel: string
  onSubmit: (values: Record<string, string>) => Promise<unknown>
  initial?: Record<string, string>
  confirm?: boolean
}) {
  const cache = useQueryClient()
  const formId = useId()
  const submitting = useRef(false)
  const [confirmOpen, setConfirmOpen] = useState(false)

  const defaultValues = Object.fromEntries(
    fields.map((f) => [f.name, initial[f.name] ?? ""]),
  )

  const schema = z.record(z.string(), z.string()).superRefine((values, ctx) => {
    for (const field of fields) {
      const value = values[field.name]?.trim() ?? ""
      if (field.required && !value)
        ctx.addIssue({
          code: "custom",
          path: [field.name],
          message: "Vui lòng nhập thông tin này",
        })
      if (value.length > 1000)
        ctx.addIssue({
          code: "custom",
          path: [field.name],
          message: "Tối đa 1000 ký tự",
        })
      if (
        field.type === "number" &&
        value &&
        (!Number.isFinite(Number(value)) ||
          (field.min !== undefined && Number(value) < field.min) ||
          (field.max !== undefined && Number(value) > field.max))
      )
        ctx.addIssue({
          code: "custom",
          path: [field.name],
          message: "Giá trị không hợp lệ",
        })
    }
  })

  const form = useForm<Record<string, string>>({
    resolver: zodResolver(schema),
    defaultValues,
  })

  const mutation = useMutation({
    mutationFn: onSubmit,
    onSuccess: async () => {
      setConfirmOpen(false)
      form.reset(defaultValues)
      toast.success("Đã lưu thành công")
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["operations"] }),
        cache.invalidateQueries({ queryKey: ["my-appointments"] }),
        cache.invalidateQueries({ queryKey: ["appointment"] }),
        cache.invalidateQueries({ queryKey: ["services"] }),
      ])
    },
    onSettled: () => {
      submitting.current = false
    },
  })

  const submit = (values: Record<string, string>) => {
    if (submitting.current) return
    submitting.current = true
    mutation.mutate(values)
  }

  const handleOpenConfirm = async () => {
    mutation.reset()
    const valid = await form.trigger()
    if (valid) {
      setConfirmOpen(true)
    }
  }

  return (
    <form className="grid gap-4" onSubmit={form.handleSubmit(submit)}>
      {fields.map((field) => (
        <div key={field.name} className="grid gap-2">
          <Label htmlFor={`${formId}-${field.name}`}>
            {field.label}
            {field.required ? " *" : ""}
          </Label>
          {field.options ? (
            <select
              id={`${formId}-${field.name}`}
              className="h-10 rounded-lg border bg-background px-3 text-sm"
              aria-invalid={Boolean(form.formState.errors[field.name])}
              aria-describedby={
                form.formState.errors[field.name]
                  ? `${formId}-${field.name}-error`
                  : undefined
              }
              {...form.register(field.name)}
            >
              <option value="">Chọn {field.label.toLowerCase()}</option>
              {field.options.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          ) : (
            <Input
              id={`${formId}-${field.name}`}
              type={field.type ?? "text"}
              min={field.min}
              max={field.max}
              aria-invalid={Boolean(form.formState.errors[field.name])}
              aria-describedby={
                form.formState.errors[field.name]
                  ? `${formId}-${field.name}-error`
                  : undefined
              }
              {...form.register(field.name)}
            />
          )}
          {form.formState.errors[field.name] && (
            <p
              id={`${formId}-${field.name}-error`}
              className="text-sm text-destructive"
            >
              {form.formState.errors[field.name]?.message}
            </p>
          )}
        </div>
      ))}
      {mutation.error && (
        <p role="alert" className="text-sm text-destructive">
          {getApiErrorMessage(mutation.error)}
        </p>
      )}
      {confirm ? (
        <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
          <Button
            type="button"
            variant="outline"
            disabled={mutation.isPending}
            onClick={handleOpenConfirm}
          >
            {submitLabel}
          </Button>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Xác nhận {submitLabel.toLowerCase()}?</DialogTitle>
            </DialogHeader>
            <DialogDescription>
              Thao tác sẽ cập nhật dữ liệu đang lưu. Kiểm tra thông tin trước
              khi xác nhận.
            </DialogDescription>
            {mutation.error && (
              <p role="alert" className="text-sm text-destructive">
                {getApiErrorMessage(mutation.error)}
              </p>
            )}
            <Button
              type="button"
              disabled={mutation.isPending}
              onClick={form.handleSubmit(submit)}
            >
              {mutation.isPending ? "Đang lưu..." : "Xác nhận"}
            </Button>
          </DialogContent>
        </Dialog>
      ) : (
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Đang lưu..." : submitLabel}
        </Button>
      )}
    </form>
  )
}
