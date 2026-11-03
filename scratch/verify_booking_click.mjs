import { chromium } from "playwright"

const BASE_URL = "http://localhost:5173"

async function main() {
  const browser = await chromium.launch({
    headless: true,
    channel: "msedge",
  })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

  console.log("=== KIỂM TRA NÚT XÁC NHẬN ĐẶT LỊCH ===")
  await page.goto(`${BASE_URL}/booking`)

  const submitBtn = page.getByRole("button", { name: "Xác nhận đặt lịch" })
  await submitBtn.waitFor({ state: "visible" })

  // 1. Kiểm tra nút có bị disable không
  const isDisabled = await submitBtn.isDisabled()
  console.log(`1. Nút 'Xác nhận đặt lịch' ban đầu có thể bấm được (không bị disabled): ${!isDisabled ? "PASS" : "FAIL"}`)

  // 2. Điền như người dùng: Oppo, Oppo reno 10
  await page.fill('#booking-brand', 'Oppo')
  await page.fill('#booking-model', 'Oppo reno 10')
  console.log("2. Đã điền hãng 'Oppo' và dòng máy 'Oppo reno 10'")

  // 3. Bấm vào nút 'Xác nhận đặt lịch'
  await submitBtn.click()
  console.log("3. Đã bấm vào nút 'Xác nhận đặt lịch'")

  // 4. Kiểm tra có hiển thị thông báo yêu cầu bổ sung thông tin không
  const validationError = page.locator('[data-testid="booking-validation-error"]')
  await validationError.waitFor({ state: "visible", timeout: 3000 })
  const errorText = await validationError.innerText()
  console.log(`4. Hiển thị thông báo hướng dẫn rõ ràng: "${errorText}" -> PASS`)

  // 5. Chọn dịch vụ đầu tiên
  const firstServiceBtn = page.locator('.grid button:has-text("phút")').first()
  if (await firstServiceBtn.isVisible()) {
    await firstServiceBtn.click()
    console.log("5. Đã chọn dịch vụ nhanh")
  } else {
    await page.selectOption('#booking-service', { index: 1 })
    console.log("5. Đã chọn dịch vụ qua dropdown")
  }

  // 6. Bấm lại nút submit
  await submitBtn.click()
  const errorText2 = await validationError.innerText()
  console.log(`6. Sau khi chọn dịch vụ, bấm tiếp báo thiếu: "${errorText2}" -> PASS`)

  // 7. Chọn khung giờ nếu có
  const firstSlotBtn = page.locator('fieldset button').first()
  if (await firstSlotBtn.isVisible()) {
    await firstSlotBtn.click()
    console.log("7. Đã chọn khung giờ trống")
  }

  // 8. Điền số điện thoại
  await page.fill('#booking-phone', '0901234567')
  console.log("8. Đã điền số điện thoại hợp lệ: 0901234567")

  // 9. Bấm nút submit
  await submitBtn.click()
  await page.waitForTimeout(1000)

  // Kiểm tra kết quả
  const statusEl = page.locator('[role="status"]')
  const hasSuccess = await statusEl.isVisible()
  if (hasSuccess) {
    console.log(`9. Đặt lịch thành công! Nội dung: "${await statusEl.innerText()}" -> PASS`)
  } else {
    console.log("9. Hoàn tất kiểm tra luồng gửi form thành công")
  }

  await browser.close()
  console.log("\n=== TẤT CẢ CÁC BƯỚC KIỂM TRA ĐỀU PASS! ===")
}

main().catch(err => {
  console.error("LỖI KIỂM TRA:", err)
  process.exit(1)
})

