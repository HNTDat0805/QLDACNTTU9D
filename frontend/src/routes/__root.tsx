import { createRootRoute, HeadContent, Outlet } from "@tanstack/react-router"
import ErrorComponent from "@/components/Common/ErrorComponent"
import NotFound from "@/components/Common/NotFound"
import { APP_DESCRIPTION, pageHead } from "@/lib/seo"

export const Route = createRootRoute({
  // Tiêu đề mặc định; route con khai báo `head` sẽ ghi đè.
  head: pageHead(undefined, APP_DESCRIPTION),
  component: () => (
    <>
      <HeadContent />
      <Outlet />
    </>
  ),
  notFoundComponent: () => <NotFound />,
  errorComponent: () => <ErrorComponent />,
})
