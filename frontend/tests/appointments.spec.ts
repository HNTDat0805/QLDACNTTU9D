import { expect, test } from "@playwright/test"

const appointmentId = "22222222-2222-4222-8222-222222222222"
test.use({ storageState: { cookies: [], origins: [] } })

test("khách xem lịch riêng và hủy lịch bằng API mock", async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem("access_token", "test-token"),
  )
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        id: "11111111-1111-4111-8111-111111111111",
        email: "customer@example.test",
        is_active: true,
        is_superuser: false,
        full_name: "Khách",
        role: "customer",
      }),
    }),
  )
  const appointment = {
    id: appointmentId,
    appointment_number: "APPT-TEST",
    appointment_date: "2030-01-15T09:00:00Z",
    status: "CONFIRMED",
    services: [
      {
        service_id: "33333333-3333-4333-8333-333333333333",
        service_name: "Thay pin",
        price_at_booking: 1,
        quantity: 1,
      },
    ],
    status_history: [],
  }
  await page.route("**/api/v1/appointments/me**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ data: [appointment], count: 1 }),
    }),
  )
  await page.route(`**/api/v1/appointments/${appointmentId}/detail`, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(appointment),
    }),
  )
  await page.route(
    `**/api/v1/appointments/${appointmentId}/cancel`,
    async (route) => {
      expect(route.request().postDataJSON()).toMatchObject({
        reason: "Đổi kế hoạch",
      })
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          message: "Đã hủy",
          data: {
            id: appointmentId,
            appointment_number: "APPT-TEST",
            status: "CANCELLED",
          },
        }),
      })
    },
  )
  await page.goto("/appointments")
  await expect(
    page.getByRole("heading", { name: "Lịch hẹn của tôi" }),
  ).toBeVisible()
  await expect(
    page.getByRole("link", { name: "Xem chi tiết" }),
  ).toHaveAttribute("href", `/appointments/${appointmentId}`)
  await page.getByRole("link", { name: "Xem chi tiết" }).click()
  await page.waitForURL(`/appointments/${appointmentId}`)
  await expect(page.getByLabel("Lý do thay đổi hoặc hủy")).toBeVisible()
  await page.reload()
  await page.getByLabel("Lý do thay đổi hoặc hủy").fill("Đổi kế hoạch")
  const cancelled = page.waitForResponse(
    (response) =>
      response.url().endsWith(`/${appointmentId}/cancel`) &&
      response.status() === 200,
  )
  await page.getByRole("button", { name: "Hủy lịch" }).click()
  await page.getByRole("button", { name: "Xác nhận hủy", exact: true }).click()
  await cancelled
  await expect(page.getByRole("status")).toContainText("Đã hủy lịch thành công")
})

test("đổi lịch giữ quyền owner và gửi ngày giờ mới", async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem("access_token", "isolated-test-session"),
  )
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({
      json: { id: appointmentId, role: "customer", is_active: true },
    }),
  )
  await page.route(`**/api/v1/appointments/${appointmentId}/detail`, (route) =>
    route.fulfill({
      json: {
        id: appointmentId,
        appointment_number: "APPT-RESCHEDULE",
        appointment_date: "2030-01-15T09:00:00Z",
        status: "CONFIRMED",
        services: [{ service_id: appointmentId, service_name: "Thay pin" }],
      },
    }),
  )
  await page.route("**/api/v1/slots/available?*", (route) =>
    route.fulfill({
      json: { available_slots: [{ start_time: "11:00", available: true }] },
    }),
  )
  await page.route(`**/api/v1/appointments/${appointmentId}`, async (route) => {
    expect(route.request().method()).toBe("PATCH")
    expect(route.request().postDataJSON()).toMatchObject({
      appointment_date: "2030-01-16",
      start_time: "11:00",
      reschedule_reason: "Đổi kế hoạch",
    })
    await route.fulfill({
      json: { appointment_id: appointmentId, message: "Đã cập nhật" },
    })
  })
  await page.goto(`/appointments/${appointmentId}`)
  await page.getByLabel("Ngày mới").fill("2030-01-16")
  await page.getByRole("button", { name: "11:00" }).click()
  await page.getByLabel("Lý do thay đổi hoặc hủy").fill("Đổi kế hoạch")
  await page.getByRole("button", { name: "Đổi lịch", exact: true }).click()
  await expect(page.getByRole("status")).toContainText("Đã đổi lịch thành công")
})
