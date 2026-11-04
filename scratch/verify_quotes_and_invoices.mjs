import { chromium } from "playwright"

const BASE_URL = "http://localhost:5173"

async function main() {
  const browser = await chromium.launch({
    headless: true,
    channel: "msedge",
  })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()

  console.log("=== KIỂM TRA BÁO GIÁ VÀ HÓA ĐƠN THEO LỊCH MỚI ===")

  // 1. Đăng nhập với tài khoản khách hàng
  await page.goto(`${BASE_URL}/login`)
  await page.fill('[data-testid="email-input"]', "customer@example.com")
  await page.fill('[data-testid="password-input"]', "admin123")
  await page.click('button[type="submit"]')
  await page.waitForURL("**/app", { timeout: 10000 })
  console.log("1. Đăng nhập thành công với customer@example.com")

  // 2. Vào trang /quotes (Báo giá)
  await page.goto(`${BASE_URL}/quotes`)
  await page.waitForSelector('h1:has-text("Báo giá sửa chữa")')
  
  // Đếm số lượng bảng / panel báo giá
  const quotePanels = page.locator('div.border.rounded-xl')
  await quotePanels.first().waitFor({ state: "visible", timeout: 5000 })
  const quoteCount = await quotePanels.count()
  console.log(`2. Số lượng báo giá hiển thị trên giao diện: ${quoteCount} báo giá`)
  if (quoteCount < 3) {
    throw new Error(`Kỳ vọng nhiều hơn 2 báo giá nhưng chỉ có ${quoteCount}`)
  }

  // Lấy danh sách các mã báo giá hiển thị
  const quoteTitles = await page.locator('h3').allInnerTexts()
  console.log("   Mã các báo giá:", quoteTitles.filter(t => t.startsWith("QUO-")))

  // 3. Vào trang /invoices (Hóa đơn & thanh toán)
  await page.goto(`${BASE_URL}/invoices`)
  await page.waitForSelector('h1:has-text("Hóa đơn & thanh toán")')

  const invoicePanels = page.locator('div.border.rounded-xl')
  await invoicePanels.first().waitFor({ state: "visible", timeout: 5000 })
  const invoiceCount = await invoicePanels.count()
  console.log(`3. Số lượng hóa đơn hiển thị trên giao diện: ${invoiceCount} hóa đơn`)
  if (invoiceCount < 3) {
    throw new Error(`Kỳ vọng nhiều hơn 2 hóa đơn nhưng chỉ có ${invoiceCount}`)
  }

  const invoiceTitles = await page.locator('h3').allInnerTexts()
  console.log("   Mã các hóa đơn:", invoiceTitles.filter(t => t.startsWith("INV-")))

  // 4. Test đặt lịch mới -> Kiểm tra báo giá tự động sinh
  console.log("4. Tiến hành đặt lịch hẹn mới tại /booking...")
  await page.goto(`${BASE_URL}/booking`)
  await page.waitForSelector('#booking-service')
  
  // Chọn dịch vụ đầu tiên
  const options = await page.locator('#booking-service option').all()
  let chosenServiceId = ""
  for (const opt of options) {
    const val = await opt.getAttribute('value')
    if (val) {
      chosenServiceId = val
      break
    }
  }
  await page.selectOption('#booking-service', chosenServiceId)
  await page.fill('#booking-date', '2026-11-28')

  // Chọn khung giờ trống đầu tiên
  const slotButton = page.locator('fieldset button').first()
  await slotButton.waitFor({ state: "visible", timeout: 5000 })
  await slotButton.click()

  // Điền số điện thoại
  await page.fill('#booking-phone', '0912345678')
  await page.fill('#booking-brand', 'Samsung')
  await page.fill('#booking-model', 'Galaxy S24')

  // Bấm Xác nhận đặt lịch
  await page.click('button[type="submit"]:has-text("Xác nhận đặt lịch")')

  // Đợi thông báo đặt lịch thành công
  const successNotice = page.locator('div[role="status"]:has-text("Đặt lịch thành công")')
  await successNotice.waitFor({ state: "visible", timeout: 8000 })
  const successText = await successNotice.innerText()
  console.log(`   ${successText.replace(/\n+/g, ' ')}`)
  const matchCode = successText.match(/APPT-\d+-[A-Z0-9]+/)
  const newApptCode = matchCode ? matchCode[0] : ""
  console.log(`   Mã lịch hẹn vừa đặt: ${newApptCode}`)

  // 5. Quay lại /quotes xem báo giá cho lịch mới
  await page.goto(`${BASE_URL}/quotes`)
  await page.waitForSelector('h1:has-text("Báo giá sửa chữa")')
  const expectedQuoteCode = newApptCode.replace("APPT", "QUO")
  const newQuoteEl = page.locator(`text=${expectedQuoteCode}`)
  await newQuoteEl.waitFor({ state: "visible", timeout: 5000 })
  console.log(`5. Đã tìm thấy báo giá tự động sinh cho lịch mới: "${expectedQuoteCode}" -> PASS!`)

  await browser.close()
  console.log("\n=== TẤT CẢ KIỂM TRA BÁO GIÁ VÀ HÓA ĐƠN ĐỀU PASS 100%! ===")
}

main().catch(err => {
  console.error("LỖI KIỂM TRA:", err)
  process.exit(1)
})

