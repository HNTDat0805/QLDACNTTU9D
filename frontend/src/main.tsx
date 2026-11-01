import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query"
import { createRouter, RouterProvider } from "@tanstack/react-router"
import { isAxiosError } from "axios"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { toast } from "sonner"
import { LoginService } from "./client"
import { client } from "./client/client.gen"
import { ThemeProvider } from "./components/theme-provider"
import { Toaster } from "./components/ui/sonner"
import "./index.css"
import { routeTree } from "./routeTree.gen"
import { getApiErrorMessage, getApiErrorStatus } from "./utils"

client.setConfig({
  baseURL: import.meta.env.VITE_API_URL ?? "",
  auth: () => localStorage.getItem("access_token") || "",
})

let refreshPromise: Promise<string | null> | null = null

const refreshAccessToken = async (): Promise<string | null> => {
  const refreshToken = localStorage.getItem("refresh_token")
  if (!refreshToken) return null

  if (!refreshPromise) {
    refreshPromise = LoginService.refreshAccessToken({
      body: { refresh_token: refreshToken },
    })
      .then(({ data }) => {
        localStorage.setItem("access_token", data.access_token)
        if (data.refresh_token) {
          localStorage.setItem("refresh_token", data.refresh_token)
        }
        return data.access_token
      })
      .catch(() => {
        localStorage.removeItem("refresh_token")
        return null
      })
      .finally(() => {
        refreshPromise = null
      })
  }

  return refreshPromise
}

client.instance.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (
      !isAxiosError(error) ||
      error.response?.status !== 401 ||
      !error.config
    ) {
      return Promise.reject(error)
    }

    const requestUrl = error.config.url ?? ""
    const isRefreshRequest = requestUrl.includes("/login/refresh-token")
    const alreadyRetried = error.config.headers?.["x-fixcare-retry"] === "true"

    if (isRefreshRequest || alreadyRetried) {
      return Promise.reject(error)
    }

    const accessToken = await refreshAccessToken()
    if (!accessToken) {
      return Promise.reject(error)
    }

    error.config.headers.set("Authorization", `Bearer ${accessToken}`)
    error.config.headers.set("x-fixcare-retry", "true")
    return client.instance.request(error.config)
  },
)

let isRedirectingToLogin = false

const redirectToLoginForExpiredSession = (error: unknown): boolean => {
  const hasAccessToken = localStorage.getItem("access_token") !== null
  const isOnLoginPage = window.location.pathname === "/login"

  if (
    getApiErrorStatus(error) !== 401 ||
    !hasAccessToken ||
    isOnLoginPage ||
    isRedirectingToLogin
  ) {
    return false
  }

  isRedirectingToLogin = true
  localStorage.removeItem("access_token")
  window.location.assign("/login")
  return true
}

const showGlobalApiError = (error: unknown) => {
  const status = getApiErrorStatus(error)
  toast.error("Yêu cầu không thành công", {
    description: getApiErrorMessage(error),
    id: `api-error-${status ?? "network"}`,
  })
}

const shouldRetryQuery = (failureCount: number, error: unknown) => {
  const status = getApiErrorStatus(error)
  const nonRetryableStatuses = [401, 403, 404, 422]

  if (status !== undefined && nonRetryableStatuses.includes(status)) {
    return false
  }

  return failureCount < 3
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: shouldRetryQuery,
    },
  },
  queryCache: new QueryCache({
    onError: (error) => {
      if (!redirectToLoginForExpiredSession(error)) {
        showGlobalApiError(error)
      }
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      if (redirectToLoginForExpiredSession(error)) {
        return
      }

      if (!mutation.options.onError) {
        showGlobalApiError(error)
      }
    },
  }),
})

const router = createRouter({ routeTree })
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <Toaster richColors closeButton />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
