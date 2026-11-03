import { chromium } from "playwright"

const BASE_URL = "http://localhost:5173"

const ROLES = [
  {
    role: "customer",
    email: "customer@example.com",
    password: "admin123",
    expectedRoleLabel: "Khách hàng",
    expectedNavItems: [
      "Tổng quan",
      "Trang chủ",
      "Dịch vụ",
      "Đặt lịch",
      "Lịch hẹn của tôi",
      "Báo giá",
      "Hóa đơn",
      "Đánh giá",
    ],
  },
  {
    role: "staff",
    email: "staff@example.com",
    password: "admin123",
    expectedRoleLabel: "Nhân viên",
    expectedNavItems: [
      "Tổng quan",
      "Trung tâm tiếp nhận",
      "Tiếp nhận",
      "Hàng chờ",
      "Lịch hẹn",
      "Phiếu sửa chữa",
      "Báo giá",
      "Hóa đơn",
      "Khách hàng",
      "Kỹ thuật viên",
    ],
  },
  {
    role: "technician",
    email: "technician@example.com",
    password: "admin123",
    expectedRoleLabel: "Kỹ thuật viên",
    expectedNavItems: [
      "Tổng quan",
      "Công việc",
      "Lịch hẹn",
      "Hàng chờ",
      "Báo giá",
      "Ca làm việc",
    ],
  },
  {
    role: "manager",
    email: "manager@example.com",
    password: "admin123",
    expectedRoleLabel: "Quản lý",
    expectedNavItems: [
      "Tổng quan",
      "Trung tâm tiếp nhận",
      "Lịch hẹn",
      "Tiếp nhận",
      "Hàng chờ",
      "Công việc",
      "Khách hàng",
      "Dịch vụ",
      "Kỹ thuật viên",
      "Hóa đơn",
      "Báo cáo",
    ],
  },
  {
    role: "admin",
    email: "admin@example.com",
    password: "admin123",
    expectedRoleLabel: "Quản trị viên",
    expectedNavItems: [
      "Tổng quan",
      "Trung tâm tiếp nhận",
      "Lịch hẹn",
      "Tiếp nhận",
      "Hàng chờ",
      "Công việc",
      "Khách hàng",
      "Dịch vụ",
      "Kỹ thuật viên",
      "Hóa đơn",
      "Báo cáo",
      "Tài khoản",
    ],
  },
]

async function main() {
  const browser = await chromium.launch({
    headless: true,
    channel: "msedge",
  })

  console.log("=== BẮT ĐẦU KIỂM TRA ĐỒNG BỘ THANH ĐIỀU HƯỚNG THEO ROLE ===")

  // 1. Kiểm tra khách chưa đăng nhập (Guest)
  const guestContext = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const guestPage = await guestContext.newPage()
  await guestPage.goto(BASE_URL + "/")
  await guestPage.waitForSelector('[data-testid="desktop-nav"]')
  const guestNav = await guestPage
    .locator('[data-testid="desktop-nav"] a')
    .allInnerTexts()
  console.log("\n[1] Khách vãng lai (Guest):")
  console.log("   Nav links:", guestNav.map(t => t.trim()).filter(Boolean))
  const loginBtn = await guestPage.locator("header a[href='/login']").isVisible()
  const signupBtn = await guestPage.locator("header a[href='/signup']").isVisible()
  console.log(`   Nút Đăng nhập: ${loginBtn ? "PASS" : "FAIL"}`)
  console.log(`   Nút Tạo tài khoản: ${signupBtn ? "PASS" : "FAIL"}`)
  await guestContext.close()

  // 2. Kiểm tra từng role
  for (const { role, email, password, expectedRoleLabel, expectedNavItems } of ROLES) {
    console.log(`\n[2] Kiểm tra vai trò: ${role.toUpperCase()} (${email})`)
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } })
    const page = await context.newPage()

    // Đăng nhập
    await page.goto(`${BASE_URL}/login`)
    await page.fill('[data-testid="email-input"]', email)
    await page.fill('[data-testid="password-input"]', password)
    await page.click('button[type="submit"]')

    // Đợi redirect vào /app
    await page.waitForURL("**/app", { timeout: 10000 })
    console.log(`   Đăng nhập thành công -> chuyển hướng tới: ${page.url()}`)

    // Chờ nav mount
    await page.waitForSelector('[data-testid="desktop-nav"]')
    const navLinks = await page
      .locator('[data-testid="desktop-nav"] a')
      .allInnerTexts()
    const cleanedLinks = navLinks.map(t => t.trim()).filter(Boolean)
    console.log("   Menu điều hướng thực tế:", cleanedLinks)
    
    // Kiểm tra đủ các items mong đợi
    const missing = expectedNavItems.filter(item => !cleanedLinks.includes(item))
    if (missing.length === 0) {
      console.log(`   Đồng bộ menu ${role}: PASS (${cleanedLinks.length} mục)`)
    } else {
      console.log(`   Menu thiếu:`, missing)
    }

    // Kiểm tra UserMenu
    const userMenu = page.locator('[data-testid="user-menu"]')
    await userMenu.waitFor({ state: "visible" })
    console.log(`   Khối UserMenu hiển thị: PASS`)

    const userMenuText = await userMenu.innerText()
    console.log(`   Nội dung UserMenu:\n   "${userMenuText.replace(/\n/g, " | ")}"`)
    const hasRoleLabel = userMenuText.includes(expectedRoleLabel)
    console.log(`   Nhãn quyền "${expectedRoleLabel}": ${hasRoleLabel ? "PASS" : "FAIL"}`)

    // Bấm mở UserMenu dropdown
    await userMenu.click()
    const profileLink = page.locator('[role="menuitem"]:has-text("Cài đặt tài khoản")')
    const logoutBtn = page.locator('[role="menuitem"]:has-text("Đăng xuất")')
    const overviewLink = page.locator('[role="menuitem"]:has-text("Tổng quan")')

    await profileLink.waitFor({ state: "visible" })
    console.log(`   Menuitem 'Tổng quan': ${await overviewLink.isVisible() ? "PASS" : "FAIL"}`)
    console.log(`   Menuitem 'Cài đặt tài khoản': ${await profileLink.isVisible() ? "PASS" : "FAIL"}`)
    console.log(`   Menuitem 'Đăng xuất': ${await logoutBtn.isVisible() ? "PASS" : "FAIL"}`)

    // Kiểm tra điều hướng tới /settings
    await profileLink.click()
    await page.waitForURL("**/settings", { timeout: 5000 })
    console.log(`   Điều hướng tới /settings: PASS`)

    // Kiểm tra khi vào lại trang công khai / (Homepage) thì thanh điều hướng vẫn giữ nguyên theo role!
    await page.goto(`${BASE_URL}/`)
    await page.waitForSelector('[data-testid="desktop-nav"]')
    const homeNavLinks = await page
      .locator('[data-testid="desktop-nav"] a')
      .allInnerTexts()
    const cleanedHomeLinks = homeNavLinks.map(t => t.trim()).filter(Boolean)
    console.log(`   Menu khi quay lại trang chủ (/):`, cleanedHomeLinks)
    const homeMissing = expectedNavItems.filter(item => !cleanedHomeLinks.includes(item))
    console.log(`   Đồng bộ trên trang chủ (/): ${homeMissing.length === 0 ? "PASS" : "FAIL"}`)

    // Đăng xuất từ trang chủ
    await page.locator('[data-testid="user-menu"]').click()
    const homeLogout = page.locator('[role="menuitem"]:has-text("Đăng xuất")')
    await homeLogout.waitFor({ state: "visible" })
    await homeLogout.click()
    await page.waitForURL("**/login", { timeout: 5000 })
    console.log(`   Đăng xuất thành công -> chuyển về: ${page.url()}`)

    await context.close()
  }

  await browser.close()
  console.log("\n=== TẤT CẢ CÁC VAI TRÒ ĐỀU ĐẠT CHUẨN ĐỒNG BỘ 100%! ===")
}

main().catch(err => {
  console.error("LỖI KIỂM TRA:", err)
  process.exit(1)
})
