import { zodResolver } from "@hookform/resolvers/zod"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { useForm } from "react-hook-form"
import { z } from "zod"

import type { Body_login_login_access_token as AccessToken } from "@/client"
import { AuthLayout } from "@/components/Common/AuthLayout"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"

const formSchema = z.object({
  username: z.email({ message: "Địa chỉ email không hợp lệ" }),
  password: z
    .string()
    .min(1, { message: "Vui lòng nhập mật khẩu" })
    .min(8, { message: "Mật khẩu phải có ít nhất 8 ký tự" }),
}) satisfies z.ZodType<AccessToken>

type FormData = z.infer<typeof formSchema>

export const Route = createFileRoute("/login")({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/app",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Đăng nhập | FixCare",
      },
    ],
  }),
})

function Login() {
  const { loginMutation } = useAuth()
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      username: "",
      password: "",
    },
  })

  const onSubmit = (data: FormData) => {
    if (loginMutation.isPending) return
    loginMutation.mutate(data)
  }

  return (
    <AuthLayout>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-6"
        >
          <div className="flex flex-col gap-1.5">
            <h1 className="text-2xl font-bold tracking-tight">Đăng nhập</h1>
            <p className="text-sm text-muted-foreground">
              Nhập thông tin tài khoản FixCare của bạn
            </p>
          </div>

          <div className="grid gap-4">
            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium">Email</FormLabel>
                  <FormControl>
                    <Input
                      data-testid="email-input"
                      placeholder="ban@example.com"
                      type="email"
                      className="h-10 transition-all duration-150 focus:border-primary/50 focus:ring-primary/20"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage className="text-xs" />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <div className="flex items-center">
                    <FormLabel className="text-sm font-medium">Mật khẩu</FormLabel>
                    <RouterLink
                      to="/recover-password"
                      className="ml-auto text-xs text-muted-foreground underline-offset-4 hover:text-primary hover:underline transition-colors"
                    >
                      Quên mật khẩu?
                    </RouterLink>
                  </div>
                  <FormControl>
                    <PasswordInput
                      data-testid="password-input"
                      placeholder="Nhập mật khẩu"
                      className="h-10 transition-all duration-150 focus:border-primary/50 focus:ring-primary/20"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage className="text-xs" />
                </FormItem>
              )}
            />

            <LoadingButton
              type="submit"
              loading={loginMutation.isPending}
              className="h-10 w-full mt-1 shadow-sm shadow-primary/20 hover:shadow-primary/30 transition-all duration-200"
            >
              Đăng nhập
            </LoadingButton>
          </div>

          <div className="text-center text-sm text-muted-foreground">
            Chưa có tài khoản?{" "}
            <RouterLink
              to="/signup"
              className="font-medium text-foreground underline underline-offset-4 hover:text-primary transition-colors"
            >
              Đăng ký ngay
            </RouterLink>
          </div>
        </form>
      </Form>
    </AuthLayout>
  )
}
