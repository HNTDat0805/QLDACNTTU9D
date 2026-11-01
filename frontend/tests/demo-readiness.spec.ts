import { expect, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })

test("demo public gọi API thật bằng GET và hiển thị catalog/empty state", async ({
  page,
}) => {
  await page.route("**/api/**", (route) => {
    if (route.request().method() !== "GET")
      return route.abort("blockedbyclient")
    return route.continue()
  })
  const servicesResponse = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/api/v1/services",
  )
  await page.goto("/services")
  const response = await servicesResponse
  expect(response.status()).toBe(200)
  expect(["localhost", "127.0.0.1"]).toContain(new URL(response.url()).hostname)
  const body = await response.json()
  await expect(
    page.getByRole("heading", { name: "Dịch vụ sửa chữa", exact: true }),
  ).toBeVisible()
  if (body.count === 0)
    await expect(
      page.getByText("Chưa có dữ liệu phù hợp. Hãy thử thay đổi bộ lọc."),
    ).toBeVisible()
  else
    await expect(
      page.getByRole("link", { name: "Xem dịch vụ" }).first(),
    ).toBeVisible()
  await page
    .getByRole("link", { name: "Đặt lịch sửa chữa", exact: true })
    .first()
    .click()
  await expect(page).toHaveURL(/\/booking$/)
  await expect(
    page.getByRole("heading", { name: "Đặt lịch sửa chữa", exact: true }),
  ).toBeVisible()
  if (body.count === 0) {
    await expect(
      page.getByText("Cửa hàng chưa có dịch vụ để đặt lịch."),
    ).toBeVisible()
    await expect(
      page.getByRole("button", { name: "Xác nhận đặt lịch" }),
    ).toBeDisabled()
  }
})
