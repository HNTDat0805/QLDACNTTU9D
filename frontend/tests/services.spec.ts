import { expect, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })
const id = "11111111-1111-4111-8111-111111111111"
test("dịch vụ công khai có chi tiết và đường dẫn đặt lịch", async ({
  page,
}) => {
  const service = {
    id,
    name: "Thay pin kiểm thử",
    description: "Kiểm tra và thay pin",
    base_price: 100000,
    estimated_duration_minutes: 30,
    is_active: true,
  }
  await page.route("**/api/v1/services", (route) =>
    route.fulfill({ json: { data: [service], count: 1 } }),
  )
  await page.route(`**/api/v1/services/${id}`, (route) =>
    route.fulfill({ json: service }),
  )
  await page.goto("/services")
  await page.getByRole("link", { name: "Xem dịch vụ" }).click()
  await expect(page.getByRole("heading", { name: service.name })).toBeVisible()
  await expect(page.getByText(service.description)).toBeVisible()
  await expect(
    page.getByRole("link", { name: "Đặt lịch sửa chữa" }).last(),
  ).toHaveAttribute("href", "/booking")
  await page.reload()
  await expect(page.getByRole("heading", { name: service.name })).toBeVisible()
  await page.goto("/about")
  await expect(page.getByRole("main")).toContainText("FixCare")
})
