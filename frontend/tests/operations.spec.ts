import { expect, type Page, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })
const id = "22222222-2222-4222-8222-222222222222"
const technicianId = "33333333-3333-4333-8333-333333333333"

async function mockSystem(page: Page, role = "staff") {
  await page.addInitScript(() =>
    localStorage.setItem("access_token", "isolated-test-session"),
  )
  const appointment = {
    id,
    appointment_number: "APPT-DEMO",
    appointment_date: "2030-01-15T09:00:00Z",
    status: "PENDING",
    customer: { full_name: "Khách kiểm thử", phone_number: "0900000000" },
    device: { id: technicianId, brand: "Test", model: "Phone" },
    services: [],
    status_history: [],
    total_amount: 100000,
  }
  const quote = {
    id,
    quote_number: "QUO-DEMO",
    appointment_id: id,
    appointment_number: "APPT-DEMO",
    total_amount: 100000,
    status: "SENT",
    device_info: "Test Phone",
    items: [{ id, item_name: "Thay pin", quantity: 1, total_price: 100000 }],
  }
  const invoice = {
    id,
    invoice_number: "INV-DEMO",
    appointment_id: id,
    status: "UNPAID",
    total_amount: 100000,
    paid_amount: 0,
    balance: 100000,
    items: [{ id, item_name: "Thay pin", quantity: 1, total_price: 100000 }],
    payments: [] as {
      id: string
      amount: number
      payment_number: string
      payment_method: string
    }[],
  }
  const notification = {
    id,
    title: "Đã tiếp nhận",
    message: "Thiết bị đã được nhận",
    is_read: false,
  }
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    let response: unknown = { data: [], count: 0 }
    if (path === "/api/v1/users/me")
      response = {
        id,
        email: "test@example.test",
        full_name: "Người kiểm thử",
        role,
        is_active: true,
        is_superuser: false,
      }
    else if (
      path === "/api/v1/appointments/history" ||
      path === "/api/v1/appointments/me" ||
      path === "/api/v1/repair-orders"
    )
      response = { data: [appointment], count: 1 }
    else if (
      path === `/api/v1/appointments/${id}/detail` ||
      path === `/api/v1/repair-orders/${id}`
    )
      response = appointment
    else if (path.endsWith("/confirm") && method === "PATCH") {
      appointment.status = "CONFIRMED"
      response = { success: true, data: appointment, message: "Đã xác nhận" }
    } else if (path === "/api/v1/technicians")
      response = {
        data: [
          { id: technicianId, full_name: "Kỹ thuật viên", is_active: true },
        ],
        count: 1,
      }
    else if (path === "/api/v1/quotes") response = { data: [quote], count: 1 }
    else if (path.endsWith("/accept")) {
      quote.status = "ACCEPTED"
      response = { success: true, data: quote }
    } else if (path.endsWith("/reject")) {
      quote.status = "REJECTED"
      response = { success: true, data: quote }
    } else if (path === "/api/v1/invoices")
      response = { data: [invoice], count: 1 }
    else if (path.endsWith("/payments")) {
      const body = route.request().postDataJSON()
      expect(body).toMatchObject({ payment_method: "CASH" })
      expect(body.request_id).toMatch(/^[0-9a-f-]{36}$/)
      invoice.paid_amount = Number(body.amount)
      invoice.balance = 100000 - Number(body.amount)
      invoice.status = invoice.balance === 0 ? "PAID" : "PARTIALLY_PAID"
      invoice.payments.push({
        id,
        amount: Number(body.amount),
        payment_number: "PAY-DEMO",
        payment_method: "CASH",
      })
      response = invoice
    } else if (path === "/api/v1/notifications")
      response = {
        data: [notification],
        count: 1,
        unread_count: notification.is_read ? 0 : 1,
      }
    else if (path.endsWith("/read")) {
      notification.is_read = true
      response = notification
    } else if (path === "/api/v1/statistics")
      response = {
        start_date: "2030-01-01",
        end_date: "2030-01-31",
        receipts_total: 100000,
        outstanding_total: 0,
        appointment_count: 1,
        completed_count: 1,
        customer_count: 1,
        monthly_revenue: [{ month: "2030-01", amount: 100000 }],
      }
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(response),
    })
  })
}

test("nhân viên xác nhận lịch và danh sách cập nhật", async ({ page }) => {
  await mockSystem(page)
  await page.goto("/workspace/appointments")
  await page.getByRole("button", { name: /APPT-DEMO/ }).click()
  await page.getByRole("button", { name: "Xác nhận lịch", exact: true }).click()
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Xác nhận", exact: true })
    .click()
  await expect(
    page.getByText("Đã xác nhận", { exact: true }).first(),
  ).toBeVisible()
})

test("kỹ thuật viên mở việc được phân công", async ({ page }) => {
  await mockSystem(page, "technician")
  await page.goto("/workspace/repairs")
  await expect(
    page.getByRole("heading", { name: "Công việc được phân công" }),
  ).toBeVisible()
  await page.getByRole("button", { name: /APPT-DEMO/ }).click()
  await expect(page.getByLabel("Trạng thái mới")).toBeVisible()
})

test("khách hàng bị chặn khỏi khu vực nhân viên", async ({ page }) => {
  await mockSystem(page, "customer")
  await page.goto("/workspace")
  await expect(page).toHaveURL(/\/app$/)
  await expect(
    page.getByRole("link", { name: "Trung tâm tiếp nhận", exact: true }),
  ).toHaveCount(0)
})

test("ghi nhận tiền tại quầy cập nhật hóa đơn", async ({ page }) => {
  await mockSystem(page)
  await page.goto("/invoices")
  await page.getByLabel("Số tiền đã nhận (VNĐ)").fill("100000")
  await page.getByLabel("Phương thức").selectOption("CASH")
  await page
    .getByRole("button", { name: "Ghi nhận thanh toán", exact: true })
    .click()
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Xác nhận", exact: true })
    .click()
  await expect(page.getByText("Đã thanh toán", { exact: true })).toBeVisible()
  await expect(page.getByText(/PAY-DEMO/)).toBeVisible()
})

test("khách duyệt báo giá và đánh dấu thông báo đã đọc", async ({ page }) => {
  await mockSystem(page, "customer")
  await page.goto("/quotes")
  await page.getByRole("button", { name: "Duyệt báo giá", exact: true }).click()
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Xác nhận", exact: true })
    .click()
  await expect(page.getByText("Đã duyệt", { exact: true })).toBeVisible()
  await page.goto("/notifications")
  await page.getByRole("button", { name: "Đánh dấu đã đọc" }).click()
  await expect(page.getByText("0 thông báo chưa đọc")).toBeVisible()
})

test("báo cáo quản trị lấy doanh thu thực thu và responsive", async ({
  page,
}) => {
  await mockSystem(page, "manager")
  for (const width of [375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto("/workspace/reports")
    await expect(
      page.getByRole("heading", { name: "Báo cáo quản trị" }),
    ).toBeVisible()
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true)
  }
})

test("thêm khách hàng có validation và cập nhật danh sách", async ({
  page,
}) => {
  await mockSystem(page)
  const customers: { id: string; full_name: string; phone_number: string }[] =
    []
  await page.route("**/api/v1/customers?*", (route) =>
    route.fulfill({ json: { data: customers, count: customers.length } }),
  )
  await page.route("**/api/v1/customers", async (route) => {
    const body = route.request().postDataJSON()
    expect(body).toMatchObject({
      full_name: "Khách mới",
      phone_number: "0900000001",
    })
    customers.push({ id, ...body })
    await route.fulfill({ json: customers[0] })
  })
  await page.goto("/workspace/customers")
  await page
    .getByRole("button", { name: "Tạo khách hàng", exact: true })
    .click()
  await expect(
    page.getByText("Vui lòng nhập thông tin này").first(),
  ).toBeVisible()
  await page.getByLabel("Họ tên", { exact: false }).fill("Khách mới")
  await page.getByLabel("Số điện thoại", { exact: false }).fill("0900000001")
  await page
    .getByRole("button", { name: "Tạo khách hàng", exact: true })
    .click()
  await expect(page.getByRole("button", { name: /Khách mới/ })).toBeVisible()
})

test("tiếp nhận máy gửi tình trạng và mô tả lỗi", async ({ page }) => {
  await mockSystem(page)
  await page.route("**/api/v1/intake", async (route) => {
    expect(route.request().postDataJSON()).toMatchObject({
      customer_name: "Khách tại quầy",
      physical_condition: "Màn hình trầy",
      fault_description: "Không lên nguồn",
    })
    await route.fulfill({ json: { success: true, data: { id } } })
  })
  await page.goto("/workspace/intake")
  await page
    .getByLabel("Tên khách hàng", { exact: false })
    .fill("Khách tại quầy")
  await page.getByLabel("Số điện thoại", { exact: false }).fill("0900000002")
  await page.getByLabel("Hãng thiết bị", { exact: false }).fill("Test")
  await page.getByLabel("Dòng máy", { exact: false }).fill("Phone")
  await page
    .getByLabel("Tình trạng ngoại quan", { exact: false })
    .fill("Màn hình trầy")
  await page.getByLabel("Mô tả lỗi", { exact: false }).fill("Không lên nguồn")
  await page.getByRole("button", { name: "Lưu phiếu tiếp nhận" }).click()
  await expect(page.getByText("Đã lưu thành công")).toBeVisible()
})

test("báo giá nhiều hạng mục giữ dữ liệu và gửi số tiền", async ({ page }) => {
  await mockSystem(page)
  await page.route("**/api/v1/quotes", async (route) => {
    if (route.request().method() !== "POST") return route.fallback()
    expect(route.request().postDataJSON()).toMatchObject({
      appointment_id: id,
      items: [
        { item_name: "Thay pin", unit_price: 100000, quantity: 1 },
        { item_name: "Vệ sinh", unit_price: 20000, quantity: 1 },
      ],
    })
    await route.fulfill({
      json: { success: true, data: { id, total_amount: 120000 } },
    })
  })
  await page.goto("/workspace/repairs")
  await page.getByRole("button", { name: /APPT-DEMO/ }).click()
  await page.getByLabel("Hạng mục 1", { exact: false }).fill("Thay pin")
  await page.getByLabel("Đơn giá 1 (VNĐ)", { exact: false }).fill("100000")
  await page.getByLabel("Số lượng 1", { exact: false }).fill("1")
  await page.getByRole("button", { name: "Thêm hạng mục" }).click()
  await expect(page.getByLabel("Hạng mục 1", { exact: false })).toHaveValue(
    "Thay pin",
  )
  await page.getByLabel("Hạng mục 2", { exact: false }).fill("Vệ sinh")
  await page.getByLabel("Đơn giá 2 (VNĐ)", { exact: false }).fill("20000")
  await page.getByLabel("Số lượng 2", { exact: false }).fill("1")
  await page.getByRole("button", { name: "Tạo báo giá gửi khách" }).click()
  await expect(page.getByText("Đã lưu thành công")).toBeVisible()
})

test("quản lý sửa giá và ngưng dịch vụ mà không xóa lịch sử", async ({
  page,
}) => {
  await mockSystem(page, "manager")
  const service = {
    id,
    name: "Dịch vụ kiểm thử",
    description: "",
    base_price: 100000,
    estimated_duration_minutes: 30,
    is_active: true,
  }
  await page.route("**/api/v1/services/manage?*", (route) =>
    route.fulfill({ json: { data: [service], count: 1 } }),
  )
  await page.route(`**/api/v1/services/${id}`, async (route) => {
    expect(route.request().method()).toBe("PUT")
    const body = route.request().postDataJSON()
    expect(body).toMatchObject({ base_price: 120000, is_active: false })
    Object.assign(service, body)
    await route.fulfill({ json: service })
  })
  await page.goto("/workspace/services")
  await page.getByRole("button", { name: /Dịch vụ kiểm thử/ }).click()
  await page.getByLabel("Giá tham khảo (VNĐ)", { exact: false }).fill("120000")
  await page.getByLabel("Trạng thái", { exact: false }).selectOption("false")
  await page.getByRole("button", { name: "Lưu dịch vụ" }).click()
  await expect(
    page.getByRole("button", { name: /Dịch vụ kiểm thử/ }),
  ).toContainText("Ngừng cung cấp")
})

test("superuser tạo tài khoản với vai trò kỹ thuật viên", async ({ page }) => {
  await mockSystem(page, "admin")
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({
      json: {
        id,
        email: "admin@example.test",
        full_name: "Quản trị kiểm thử",
        role: "admin",
        is_active: true,
        is_superuser: true,
      },
    }),
  )
  await page.route("**/api/v1/users/?*", (route) =>
    route.fulfill({ json: { data: [], count: 0 } }),
  )
  await page.route("**/api/v1/users/", async (route) => {
    expect(route.request().postDataJSON()).toMatchObject({
      role: "technician",
      is_active: true,
    })
    await route.fulfill({ json: { id, role: "technician", is_active: true } })
  })
  await page.goto("/admin")
  await page.getByRole("button", { name: "Add User" }).click()
  const dialog = page.getByRole("dialog")
  await dialog
    .getByPlaceholder("Email", { exact: true })
    .fill("technician@example.test")
  const testPassword = `test-only-${crypto.randomUUID()}`
  await dialog
    .getByPlaceholder("Password", { exact: true })
    .nth(0)
    .fill(testPassword)
  await dialog
    .getByPlaceholder("Password", { exact: true })
    .nth(1)
    .fill(testPassword)
  await dialog.getByLabel("Vai trò").selectOption("technician")
  await dialog.getByRole("checkbox", { name: "Is active?" }).check()
  await dialog.getByRole("button", { name: "Save", exact: true }).click()
  await expect(dialog).not.toBeVisible()
})

test("đặt chỗ nhanh xuất hiện trong hàng chờ", async ({ page }) => {
  await mockSystem(page)
  let added = false
  await page.route("**/api/v1/services", (route) =>
    route.fulfill({ json: { data: [{ id, name: "Thay pin" }], count: 1 } }),
  )
  await page.route("**/api/v1/queue**", async (route) => {
    if (route.request().method() === "POST") {
      expect(route.request().postDataJSON()).toMatchObject({
        customer_name: "Khách đặt chỗ",
        service_id: id,
        appointment_date: "2030-01-15",
        start_time: "09:00",
      })
      added = true
    }
    await route.fulfill({
      json: {
        data: added
          ? [
              {
                appointment_id: id,
                appointment_number: "APPT-QUEUE",
                customer_name: "Khách đặt chỗ",
                appointment_date: "2030-01-15T09:00:00Z",
                status: "PENDING",
                queue_position: 1,
              },
            ]
          : [],
        count: added ? 1 : 0,
      },
    })
  })
  await page.goto("/workspace/queue")
  await page.getByLabel("Tên khách", { exact: false }).fill("Khách đặt chỗ")
  await page
    .getByLabel("Số điện thoại khách", { exact: false })
    .fill("0900000003")
  await page.getByLabel("Dịch vụ", { exact: false }).selectOption(id)
  await page.getByLabel("Ngày đặt chỗ", { exact: false }).fill("2030-01-15")
  await page.getByLabel("Giờ đặt chỗ", { exact: false }).fill("09:00")
  await page.getByRole("button", { name: "Thêm vào hàng chờ" }).click()
  await expect(page.getByText(/Khách đặt chỗ · APPT-QUEUE/)).toBeVisible()
})

test("quản lý chọn tài khoản kỹ thuật viên và sửa ca làm", async ({ page }) => {
  await mockSystem(page, "manager")
  await page.route("**/api/v1/technicians/accounts", (route) =>
    route.fulfill({
      json: [
        { id, full_name: "Tài khoản kỹ thuật", email: "tech@example.test" },
      ],
    }),
  )
  const schedule = {
    id,
    technician_id: technicianId,
    work_date: "2030-01-15",
    start_time: "08:00:00",
    end_time: "17:00:00",
    status: "AVAILABLE",
  }
  await page.route("**/api/v1/work-schedules?*", (route) =>
    route.fulfill({ json: { data: [schedule], count: 1 } }),
  )
  await page.route(`**/api/v1/work-schedules/${id}`, async (route) => {
    expect(route.request().postDataJSON()).toMatchObject({
      start_time: "09:00",
      end_time: "16:00",
    })
    Object.assign(schedule, route.request().postDataJSON())
    await route.fulfill({ json: schedule })
  })
  await page.goto("/workspace/technicians")
  await page
    .getByLabel("Tài khoản kỹ thuật viên", { exact: false })
    .selectOption(id)
  await expect(
    page.getByLabel("Tài khoản kỹ thuật viên", { exact: false }),
  ).toHaveValue(id)
  await page
    .getByRole("button", { name: /Kỹ thuật viên.*Chưa ghi chuyên môn/ })
    .click()
  await page.getByLabel("Giờ bắt đầu ca", { exact: false }).fill("09:00")
  await page.getByLabel("Giờ kết thúc ca", { exact: false }).fill("16:00")
  await page.getByRole("button", { name: "Đổi giờ ca làm" }).click()
  await expect(page.getByText(/2030-01-15 · 09:00–16:00/)).toBeVisible()
})

test("khách đánh giá lịch hoàn tất và thấy đánh giá vừa gửi", async ({
  page,
}) => {
  await mockSystem(page, "customer")
  const reviews: {
    id: string
    appointment_id: string
    rating: number
    comment: string
  }[] = []
  await page.route("**/api/v1/appointments/me?*", (route) =>
    route.fulfill({
      json: {
        data: [{ id, appointment_number: "APPT-DONE", status: "COMPLETED" }],
        count: 1,
      },
    }),
  )
  await page.route("**/api/v1/reviews**", async (route) => {
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON()
      expect(body).toMatchObject({
        appointment_id: id,
        rating: 5,
        comment: "Sửa tốt",
      })
      reviews.push({ id, ...body })
      return route.fulfill({ json: reviews[0] })
    }
    await route.fulfill({ json: { data: reviews, count: reviews.length } })
  })
  await page.goto("/reviews")
  await page
    .getByLabel("Lịch hẹn đã hoàn tất", { exact: false })
    .selectOption(id)
  await page.getByLabel("Số sao", { exact: false }).selectOption("5")
  await page.getByLabel("Nhận xét", { exact: true }).fill("Sửa tốt")
  await page.getByRole("button", { name: "Gửi đánh giá", exact: true }).click()
  await expect(page.getByRole("heading", { name: "5/5 sao" })).toBeVisible()
  await expect(page.getByText("Sửa tốt", { exact: true })).toBeVisible()
})

test("dashboard nhân viên hiển thị KPI từ API và link xử lý", async ({
  page,
}) => {
  await mockSystem(page)
  await page.goto("/workspace")
  await expect(
    page.getByRole("heading", { name: "Trung tâm tiếp nhận" }),
  ).toBeVisible()
  await expect(
    page.getByRole("link", { name: /Chờ xác nhận 1/ }),
  ).toHaveAttribute("href", "/workspace/appointments")
  await expect(
    page.getByRole("link", { name: /Lịch đã xác nhận 1/ }),
  ).toBeVisible()
  await expect(
    page.getByRole("link", { name: /Trong hàng chờ 0/ }),
  ).toBeVisible()
})

test("dashboard kỹ thuật viên hiển thị việc được giao", async ({ page }) => {
  await mockSystem(page, "technician")
  await page.goto("/app")
  await expect(
    page.getByText("Công việc kỹ thuật", { exact: true }),
  ).toBeVisible()
  await expect(page.getByText("APPT-DEMO", { exact: true })).toBeVisible()
  await expect(
    page.getByRole("link", { name: "Xem việc được phân công" }),
  ).toHaveAttribute("href", "/workspace/repairs")
})
