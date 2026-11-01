import { expect, test } from "@playwright/test"

const currentUser = {
  id: "00000000-0000-0000-0000-000000000001",
  email: "customer@example.com",
  full_name: "Khách hàng thử nghiệm",
  is_active: true,
  is_superuser: false,
  role: "customer",
}

test.use({ storageState: { cookies: [], origins: [] } })

test("trang công khai hiển thị được khi chưa đăng nhập", async ({ page }) => {
  await page.goto("/")

  await expect(
    page.getByRole("heading", {
      name: "Gửi gắm thiết bị, theo dõi sửa chữa thật rõ ràng.",
    }),
  ).toBeVisible()
  await expect(
    page
      .getByRole("navigation", { name: "Điều hướng công khai" })
      .getByRole("link", { name: "Đăng nhập" }),
  ).toBeVisible()
})

test("khách chưa đăng nhập bị chuyển khỏi khu vực làm việc", async ({
  page,
}) => {
  await page.goto("/app")
  await page.waitForURL("/login")
})

test("sidebar mobile mở, đóng và giao diện đổi theme", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 })
  await page.route("**/api/v1/users/me", async (route) => {
    await route.fulfill({ contentType: "application/json", json: currentUser })
  })
  // The dashboard now loads customer activity; keep the fake session isolated from the real API.
  await page.route("**/api/v1/appointments/me**", (route) =>
    route.fulfill({ json: { data: [], count: 0 } }),
  )
  await page.goto("/login")
  await page.evaluate(() => localStorage.setItem("access_token", "test-token"))
  await page.goto("/app")

  const sidebarButton = page.getByRole("button", {
    name: "Mở hoặc đóng thanh điều hướng",
  })
  await expect(sidebarButton).toBeVisible()
  await sidebarButton.click()
  await expect(page.getByRole("link", { name: "Tổng quan" })).toBeVisible()
  await page.getByRole("link", { name: "Tổng quan" }).click()
  await expect(page.getByRole("link", { name: "Tổng quan" })).not.toBeVisible()

  await page.goto("/")
  await page.getByTestId("theme-button").click()
  await page.getByTestId("dark-mode").click()
  await expect(page.locator("html")).toHaveClass(/dark/)
})

test("bố cục công khai đáp ứng trên mobile, tablet và desktop", async ({
  page,
}) => {
  for (const width of [375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto("/")
    await expect(
      page.getByRole("navigation", { name: "Điều hướng công khai" }),
    ).toBeVisible()
    await expect(
      page.locator("footer").filter({ hasText: "FixCare · Quản lý sửa chữa" }),
    ).toBeVisible()
  }
})
