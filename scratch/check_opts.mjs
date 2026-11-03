import { chromium } from "playwright"

async function main() {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' })
  const page = await browser.newPage()
  await page.goto('http://localhost:5173/login')
  await page.fill('[data-testid="email-input"]', 'customer@example.com')
  await page.fill('[data-testid="password-input"]', 'admin123')
  await page.click('button[type="submit"]')
  await page.waitForURL('**/app')
  await page.goto('http://localhost:5173/reviews')
  await page.waitForSelector('select')
  const opts = await page.locator('select').first().locator('option').allInnerTexts()
  console.log('DANH SÁCH LỊCH HẸN HOÀN TẤT TRONG DROPDOWN:')
  opts.forEach((o, i) => console.log(`  [${i}] ${o}`))
  await browser.close()
}

main().catch(console.error)

