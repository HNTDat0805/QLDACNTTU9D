import { chromium } from "playwright"

async function run() {
  const browser = await chromium.launch({ channel: "msedge" })
  const page = await browser.newPage()
  const appointmentId = "44444444-4444-4444-8444-444444444444"

  console.log("=== KIỂM TRA 2 NÚT ĐỔI LỊCH VÀ HỦY LỊCH ===")

  await page.addInitScript(() => localStorage.setItem("access_token", "test-token-reschedule"))
  
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({
      json: {
        id: "11111111-1111-4111-8111-111111111111",
        email: "customer@example.test",
        is_active: true,
        is_superuser: false,
        full_name: "Khách hàng thử nghiệm",
        role: "customer",
      },
    })
  )

  const appointment = {
    id: appointmentId,
    appointment_number: "APPT-BUTTON-TEST",
    appointment_date: "2026-11-28T09:00:00Z",
    status: "CONFIRMED",
    services: [
      {
        service_id: "76839d2a-a4e6-4827-b5a7-17d294e129ef",
        service_name: "Thay màn hình OLED",
        price_at_booking: 1200000,
        quantity: 1,
      },
    ],
    status_history: [],
  }

  await page.route(`**/api/v1/appointments/${appointmentId}/detail`, (route) =>
    route.fulfill({ json: appointment })
  )

  await page.route("**/api/v1/slots/available?*", (route) =>
    route.fulfill({
      json: {
        date: "2026-11-29",
        available_slots: [
          { start_time: "09:00", available: true },
          { start_time: "10:00", available: true },
          { start_time: "14:00", available: true },
        ],
      },
    })
  )

  let cancelPayload = null
  await page.route(`**/api/v1/appointments/${appointmentId}/cancel`, async (route) => {
    cancelPayload = route.request().postDataJSON()
    await route.fulfill({
      json: {
        success: true,
        message: "Đã hủy thành công",
        data: { id: appointmentId, status: "CANCELLED" },
      },
    })
  })

  let reschedulePayload = null
  await page.route(`**/api/v1/appointments/${appointmentId}`, async (route) => {
    reschedulePayload = route.request().postDataJSON()
    await route.fulfill({
      json: {
        appointment_id: appointmentId,
        message: "Đã cập nhật lịch thành công",
      },
    })
  })

  await page.goto(`http://localhost:5173/appointments/${appointmentId}`)
  await page.waitForLoadState("networkidle")

  const rescheduleBtn = page.getByRole("button", { name: "Đổi lịch", exact: true })
  const cancelBtn = page.getByRole("button", { name: "Hủy lịch", exact: true })

  // 1. Kiểm tra 2 nút KHÔNG bị vô hiệu hóa khi form trống
  console.log("1. Kiểm tra trạng thái bấm được của 2 nút...")
  const isRescheduleDisabled = await rescheduleBtn.isDisabled()
  const isCancelDisabled = await cancelBtn.isDisabled()
  console.log("  - Đổi lịch is disabled:", isRescheduleDisabled)
  console.log("  - Hủy lịch is disabled:", isCancelDisabled)

  if (isRescheduleDisabled || isCancelDisabled) {
    throw new Error("LỖI: Nút vẫn bị disabled cứng khi chưa điền thông tin!")
  }

  // 2. Bấm Đổi lịch khi chưa chọn ngày
  console.log("2. Bấm Đổi lịch khi chưa chọn ngày...")
  await rescheduleBtn.click()
  const errorAlert1 = await page.getByRole("alert").innerText()
  console.log("  -> Thông báo:", errorAlert1)
  if (!errorAlert1.includes("chọn ngày mới")) {
    throw new Error("LỖI: Không hiển thị nhắc nhở chọn ngày mới!")
  }

  // 3. Chọn ngày nhưng chưa chọn giờ
  console.log("3. Chọn ngày 2026-11-29...")
  await page.getByLabel("Ngày mới").fill("2026-11-29")
  await page.waitForSelector("button:has-text('09:00')")
  console.log("  -> Đã tải 3 khung giờ trống: 09:00, 10:00, 14:00")

  console.log("4. Bấm Đổi lịch khi chưa chọn khung giờ...")
  await rescheduleBtn.click()
  const errorAlert2 = await page.getByRole("alert").innerText()
  console.log("  -> Thông báo:", errorAlert2)
  if (!errorAlert2.includes("khung giờ trống")) {
    throw new Error("LỖI: Không hiển thị nhắc nhở chọn khung giờ!")
  }

  // 5. Chọn giờ 10:00 và bấm Đổi lịch
  console.log("5. Chọn giờ 10:00 và bấm Đổi lịch...")
  await page.getByRole("button", { name: "10:00" }).click()
  await rescheduleBtn.click()
  await page.waitForTimeout(500)
  console.log("  -> Reschedule payload gửi đi:", reschedulePayload)
  if (reschedulePayload?.start_time !== "10:00" || reschedulePayload?.appointment_date !== "2026-11-29") {
    throw new Error("LỖI: Payload đổi lịch không khớp!")
  }

  // 6. Kiểm tra nút Hủy lịch khi chưa nhập lý do trước
  console.log("6. Bấm Hủy lịch mà không cần nhập lý do trước...")
  await cancelBtn.click()
  const dialogTitle = await page.getByRole("heading", { name: "Xác nhận hủy lịch?" })
  await dialogTitle.waitFor({ state: "visible" })
  console.log("  -> Hộp thoại hủy lịch đã mở thành công!")

  // Bấm chọn gợi ý nhanh "Bận việc đột xuất"
  console.log("7. Bấm chọn gợi ý nhanh 'Bận việc đột xuất' trong hộp thoại...")
  await page.getByRole("button", { name: "Bận việc đột xuất" }).click()
  const reasonVal = await page.locator("#cancel-dialog-reason").inputValue()
  console.log("  -> Giá trị lý do được điền tự động:", reasonVal)
  if (reasonVal !== "Bận việc đột xuất") {
    throw new Error("LỖI: Nút gợi ý nhanh không điền vào ô lý do!")
  }

  // Xác nhận hủy
  console.log("8. Bấm 'Xác nhận hủy'...")
  await page.getByRole("button", { name: "Xác nhận hủy", exact: true }).click()
  await page.waitForTimeout(500)
  console.log("  -> Cancel payload gửi đi:", cancelPayload)
  if (cancelPayload?.reason !== "Bận việc đột xuất") {
    throw new Error("LỖI: Payload hủy lịch không khớp!")
  }

  await browser.close()
  console.log("✅ TẤT CẢ CÁC BƯỚC XÁC THỰC 2 NÚT ĐỔI LỊCH VÀ HỦY LỊCH ĐỀU ĐẠT CHUẨN 100%!")
}

run().catch((e) => {
  console.error("❌ Thất bại:", e)
  process.exit(1)
})

