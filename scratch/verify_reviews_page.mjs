import { chromium } from "playwright"

const BASE_URL = "http://localhost:5173"

async function main() {
  const browser = await chromium.launch({
    headless: true,
    channel: "msedge",
  })
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await context.newPage()

  page.on('response', async resp => {
    if (resp.url().includes('/api/v1/reviews') || resp.url().includes('/api/v1/commerce/reviews')) {
      console.log(`API [${resp.request().method()}] ${resp.url()} -> ${resp.status()}`)
      try {
        const text = await resp.text()
        console.log(`   Response: ${text.slice(0, 200)}`)
      } catch (e) {}
    }
  })

  // Đăng nhập
  await page.goto(`${BASE_URL}/login`)
  await page.fill('[data-testid="email-input"]', "customer@example.com")
  await page.fill('[data-testid="password-input"]', "admin123")
  await page.click('button[type="submit"]')
  await page.waitForURL("**/app", { timeout: 10000 })
  console.log("1. Đăng nhập thành công với customer@example.com")

  // Vào trang /reviews
  await page.goto(`${BASE_URL}/reviews`)
  await page.waitForSelector('h1:has-text("Đánh giá dịch vụ")')
  console.log("2. Đã mở trang /reviews")

  const selectLocator = page.locator('select').first()
  await selectLocator.waitFor({ state: "visible", timeout: 5000 })
  const options = await selectLocator.locator('option').allInnerTexts()
  console.log("3. Tùy chọn lịch hẹn:", options)

  // Chọn option 1
  await selectLocator.selectOption({ index: 1 })
  console.log("4. Đã chọn lịch hẹn")

  // Chọn số sao (select thứ 2)
  const ratingSelect = page.locator('select').nth(1)
  await ratingSelect.selectOption("5")
  console.log("5. Đã chọn 5 sao")

  // Điền nhận xét
  await page.locator('input[id*="comment"]').fill("Dịch vụ sửa chữa rất tốt và chuyên nghiệp!")
  console.log("6. Đã nhập nhận xét")

  // Bấm Gửi đánh giá
  const submitBtn = page.getByRole("button", { name: "Gửi đánh giá", exact: true })
  await submitBtn.click()
  console.log("7. Đã bấm nút 'Gửi đánh giá'")

  await page.waitForTimeout(2000)

  // Kiểm tra thông báo lỗi nếu có
  const errorAlert = page.locator('role=alert')
  if (await errorAlert.isVisible()) {
    console.log("LỖI MUTATION:", await errorAlert.innerText())
  } else {
    console.log("Không có lỗi, thành công!")
  }

  await browser.close()
}

main().catch(err => {
  console.error("LỖI:", err)
  process.exit(1)
})
