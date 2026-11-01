import { expect, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })

test("landing page hiển thị nội dung và CTA công khai", async ({ page }) => {
  await page.goto("/")
  await expect(
    page.getByRole("heading", {
      name: "Gửi gắm thiết bị, theo dõi sửa chữa thật rõ ràng.",
    }),
  ).toBeVisible()
  await expect(
    page.getByRole("heading", {
      name: "Bốn bước để thông tin không bị bỏ sót.",
    }),
  ).toBeVisible()
  await expect(
    page
      .getByRole("contentinfo")
      .getByText("FixCare · Quản lý sửa chữa điện thoại"),
  ).toBeVisible()
  await expect(
    page.getByRole("link", { name: "Tạo tài khoản" }).first(),
  ).toHaveAttribute("href", "/signup")
  await expect(
    page.getByRole("link", { name: "Đăng nhập" }).first(),
  ).toHaveAttribute("href", "/login")
})

test("landing page không tràn ngang ở các kích thước chính", async ({
  page,
}) => {
  for (const width of [375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto("/")
    await expect(page.locator("#landing-title")).toBeVisible()
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true)
  }
})

test("landing page có thể điều hướng bằng bàn phím và đổi dark mode", async ({
  page,
}) => {
  await page.goto("/")
  const themeButton = page.getByTestId("theme-button")
  await themeButton.focus()
  await expect(themeButton).toBeFocused()
  await themeButton.press("Enter")
  const darkMode = page.getByTestId("dark-mode")
  await darkMode.press("Enter")
  await expect(page.locator("html")).toHaveClass(/dark/)

  await themeButton.press("Enter")
  const lightMode = page.getByTestId("light-mode")
  await lightMode.press("Enter")
  await expect(page.locator("html")).not.toHaveClass(/dark/)
})
