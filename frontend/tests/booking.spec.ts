import { expect, type Page, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })

const serviceId = "11111111-1111-4111-8111-111111111111"

async function mockBookingApi(page: Page) {
  await page.route("**/api/v1/slots/technicians?*", (route) =>
    route.fulfill({ json: [] }),
  )
  await page.route("**/api/v1/services", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        data: [
          { id: serviceId, name: "Thay pin", estimated_duration_minutes: 30 },
        ],
        count: 1,
      }),
    }),
  )
  await page.route("**/api/v1/slots/available?*", async (route) => {
    expect(new URL(route.request().url()).searchParams.get("service_id")).toBe(
      serviceId,
    )
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        available_slots: [{ start_time: "09:00", available: true }],
      }),
    })
  })
}

async function completeForm(page: Page) {
  await page.getByLabel("Dịch vụ").selectOption(serviceId)
  await page.getByLabel("Ngày hẹn").fill("2030-01-15")
  await page.getByRole("button", { name: "09:00" }).click()
  await page.getByLabel("Số điện thoại").fill("0900000000")
}

test("trang đặt lịch tải dịch vụ, slot và gửi payload hợp lệ", async ({
  page,
}) => {
  await mockBookingApi(page)
  await page.route("**/api/v1/appointments", async (route) => {
    expect(route.request().postDataJSON()).toMatchObject({
      service_id: serviceId,
      appointment_date: "2030-01-15",
      start_time: "09:00",
      customer_phone: "0900000000",
    })
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        appointment_code: "APPT-TEST",
        id: "22222222-2222-4222-8222-222222222222",
      }),
    })
  })
  await page.goto("/booking")
  await expect(
    page.getByRole("heading", { name: "Đặt lịch sửa chữa" }),
  ).toBeVisible()
  await expect(page.getByRole("option", { name: /Thay pin/ })).toHaveCount(1)
  await completeForm(page)
  await page.getByRole("button", { name: "Xác nhận đặt lịch" }).click()
  await expect(page.getByRole("status")).toContainText("Đặt lịch thành công")
})

test("lỗi API hiển thị và double click chỉ gửi một yêu cầu", async ({
  page,
}) => {
  let requests = 0
  await mockBookingApi(page)
  await page.route("**/api/v1/appointments", async (route) => {
    requests += 1
    await new Promise((resolve) => setTimeout(resolve, 100))
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Không thể đặt lịch" }),
    })
  })
  await page.goto("/booking")
  await completeForm(page)
  await page.getByRole("button", { name: "Xác nhận đặt lịch" }).dblclick()
  await expect(page.getByRole("alert")).toBeVisible()
  await expect.poll(() => requests).toBe(1)
})

test("chọn kỹ thuật viên là tùy chọn và được gửi đúng vào slot, booking", async ({
  page,
}) => {
  const technicianId = "33333333-3333-4333-8333-333333333333"
  await mockBookingApi(page)
  await page.route("**/api/v1/slots/technicians?*", (route) =>
    route.fulfill({
      json: [{ id: technicianId, full_name: "Kỹ thuật viên thử nghiệm" }],
    }),
  )
  await page.route("**/api/v1/appointments", async (route) => {
    expect(route.request().postDataJSON().technician_id).toBe(technicianId)
    await route.fulfill({
      status: 201,
      json: { appointment_code: "APPT-TECH" },
    })
  })
  await page.goto("/booking")
  await page.getByLabel("Dịch vụ", { exact: true }).selectOption(serviceId)
  await page.getByLabel("Ngày hẹn").fill("2030-01-15")
  const slots = page.waitForRequest(
    (request) =>
      request.url().includes("/slots/available") &&
      new URL(request.url()).searchParams.get("technician_id") === technicianId,
  )
  await page.getByLabel("Kỹ thuật viên (tùy chọn)").selectOption(technicianId)
  await slots
  await page.getByRole("button", { name: "09:00" }).click()
  await page.getByLabel("Số điện thoại").fill("0900000000")
  await page.getByRole("button", { name: "Xác nhận đặt lịch" }).click()
  await expect(page.getByRole("status")).toContainText("APPT-TECH")
})
