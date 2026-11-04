import { chromium } from "playwright"

async function verify() {
  const browser = await chromium.launch({ channel: "msedge" })
  const context = await browser.newContext()
  const page = await context.newPage()

  console.log("=== BẮT ĐẦU KIỂM TRA TOÀN DIỆN FIXPHONE ===")

  // 1. Kiểm tra Favicon trên trang chủ
  await page.goto("http://localhost:5173")
  const iconSvg = await page.locator('link[type="image/svg+xml"]').getAttribute("href")
  const iconIco = await page.locator('link[rel="shortcut icon"]').getAttribute("href")
  console.log("1. Favicon links:", { iconSvg, iconIco })
  if (!iconSvg?.includes("favicon.svg") || !iconIco?.includes("favicon.ico")) {
    throw new Error("Favicon tags missing or incorrect!")
  }

  // 2. Kiểm tra vai trò Khách hàng (Customer)
  const customerUser = {
    id: "00000000-0000-0000-0000-000000000001",
    email: "customer@example.com",
    full_name: "Nguyễn Văn A",
    is_active: true,
    is_superuser: false,
    role: "customer",
  }

  await page.route("**/api/v1/users/me", async (route) => {
    await route.fulfill({ contentType: "application/json", json: customerUser })
  })
  await page.route("**/api/v1/appointments/me**", (route) =>
    route.fulfill({ json: { data: [], count: 0 } }),
  )

  await page.evaluate(() => localStorage.setItem("access_token", "test-token-customer"))
  await page.goto("http://localhost:5173")
  await page.waitForLoadState("networkidle")

  // Kiểm tra thanh điều hướng desktop của Khách hàng
  const desktopNavLinks = await page.locator('[data-testid="desktop-nav"] a').allInnerTexts()
  console.log("2. Khách hàng desktop nav links:", desktopNavLinks)
  if (desktopNavLinks.includes("Tổng quan")) {
    throw new Error("LỖI: Khách hàng vẫn còn mục 'Tổng quan' trên thanh điều hướng!")
  }
  if (!desktopNavLinks.includes("Trang chủ")) {
    throw new Error("LỖI: Khách hàng thiếu mục 'Trang chủ'!")
  }

  // Kiểm tra UserMenu của Khách hàng (Họ tên, Vai trò, Avatar hồng "NA")
  const userMenuBtn = page.getByTestId("user-menu")
  await userMenuBtn.waitFor({ state: "visible" })
  const userMenuText = await userMenuBtn.innerText()
  console.log("3. Khách hàng UserMenu text:", userMenuText.replace(/\n/g, " | "))
  if (!userMenuText.includes("Nguyễn Văn A") || !userMenuText.includes("Khách hàng") || !userMenuText.includes("NA")) {
    throw new Error("LỖI: UserMenu không hiển thị đúng thông tin khách hàng!")
  }

  // Bấm mở dropdown menu của UserMenu
  await userMenuBtn.click()
  const dropdownTexts = await page.locator('[role="menuitem"]').allInnerTexts()
  console.log("4. Khách hàng UserMenu dropdown items:", dropdownTexts)
  if (dropdownTexts.some(t => t.includes("Tổng quan"))) {
    throw new Error("LỖI: Khách hàng vẫn thấy 'Tổng quan' trong dropdown UserMenu!")
  }
  if (!dropdownTexts.some(t => t.includes("Trang chủ"))) {
    throw new Error("LỖI: Khách hàng thiếu 'Trang chủ' trong dropdown UserMenu!")
  }
  if (!dropdownTexts.some(t => t.includes("Cài đặt tài khoản")) || !dropdownTexts.some(t => t.includes("Đăng xuất"))) {
    throw new Error("LỖI: Dropdown thiếu Cài đặt hoặc Đăng xuất!")
  }

  // Đóng dropdown bằng cách click ra ngoài
  await page.keyboard.press("Escape")

  // 3. Kiểm tra vai trò Quản lý / Admin (Phải có 'Tổng quan')
  const adminContext = await browser.newContext()
  const adminPage = await adminContext.newPage()

  const adminUser = {
    id: "00000000-0000-0000-0000-000000000099",
    email: "admin@fixphone.test",
    full_name: "Admin FixPhone",
    is_active: true,
    is_superuser: true,
    role: "admin",
  }
  await adminPage.route("**/api/v1/users/me", async (route) => {
    await route.fulfill({ contentType: "application/json", json: adminUser })
  })
  await adminPage.goto("http://localhost:5173")
  await adminPage.evaluate(() => localStorage.setItem("access_token", "admin-token"))
  await adminPage.goto("http://localhost:5173")
  await adminPage.waitForLoadState("networkidle")

  const adminNavLinks = await adminPage.locator('[data-testid="desktop-nav"] a').allInnerTexts()
  console.log("5. Admin desktop nav links:", adminNavLinks)
  if (!adminNavLinks.includes("Tổng quan")) {
    throw new Error("LỖI: Admin bị mất mục 'Tổng quan'!")
  }

  const adminMenuBtn = adminPage.getByTestId("user-menu")
  await adminMenuBtn.click()
  const adminDropdownTexts = await adminPage.locator('[role="menuitem"]').allInnerTexts()
  console.log("6. Admin UserMenu dropdown items:", adminDropdownTexts)
  if (!adminDropdownTexts.some(t => t.includes("Tổng quan"))) {
    throw new Error("LỖI: Admin bị mất 'Tổng quan' trong dropdown UserMenu!")
  }

  await browser.close()
  console.log("✅ TẤT CẢ CÁC ĐIỀU KIỆN ĐỀU ĐẠT CHUẨN 100%!")
}

verify().catch((err) => {
  console.error("❌ Thất bại:", err)
  process.exit(1)
})
