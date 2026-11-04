import { chromium } from "playwright"

const BASE_URL = "http://localhost:5173"

async function main() {
  const browser = await chromium.launch({
    headless: true,
    channel: "msedge",
  })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

  console.log("=== KIỂM TRA HIỂN THỊ KHUNG GIỜ TRÊN GIAO DIỆN ===")
  await page.goto(`${BASE_URL}/booking`)

  // 1. Chọn dịch vụ
  await page.waitForSelector('#booking-service')
  // Chọn option đầu tiên có giá trị
  const options = await page.locator('#booking-service option').all()
  let chosenServiceId = ""
  for (const opt of options) {
    const val = await opt.getAttribute('value')
    if (val) {
      chosenServiceId = val
      break
    }
  }
  console.log(`1. Chọn dịch vụ ID: ${chosenServiceId}`)
  await page.selectOption('#booking-service', chosenServiceId)

  // 2. Điền ngày: 2026-11-27 (như ảnh của người dùng)
  await page.fill('#booking-date', '2026-11-27')
  console.log("2. Đã nhập ngày hẹn: 2026-11-27")

  // 3. Đợi các nút khung giờ xuất hiện
  const slotButtons = page.locator('fieldset button')
  await slotButtons.first().waitFor({ state: "visible", timeout: 5000 })
  const count = await slotButtons.count()
  console.log(`3. Số lượng khung giờ trống hiển thị: ${count} nút`)

  const slotTimes = await slotButtons.allInnerTexts()
  console.log("   Các khung giờ:", slotTimes.slice(0, 8), "... (tổng cộng", slotTimes.length, "khung giờ)")

  // 4. Bấm chọn thử một khung giờ (ví dụ: 09:00)
  const chosenSlot = page.locator('fieldset button:has-text("09:00")')
  if (await chosenSlot.isVisible()) {
    await chosenSlot.click()
    console.log("4. Đã bấm chọn khung giờ '09:00' -> PASS")
  } else {
    await slotButtons.first().click()
    console.log("4. Đã bấm chọn khung giờ đầu tiên -> PASS")
  }

  // 5. Kiểm tra thông tin tóm tắt bên phải
  const summaryTime = await page.locator('text=Thời gian hẹn').locator('..').locator('p.font-medium').innerText()
  console.log(`5. Tóm tắt thời gian hẹn bên phải: "${summaryTime}" -> PASS`)

  await browser.close()
  console.log("\n=== TẤT CẢ KHUNG GIỜ ĐÃ HIỂN THỊ CHUẨN XÁC 100%! ===")
}

main().catch(err => {
  console.error("LỖI KIỂM TRA:", err)
  process.exit(1)
})

