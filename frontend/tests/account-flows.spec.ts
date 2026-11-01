import { expect, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })

test("đổi tài khoản không hiển thị lại báo giá của phiên trước", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.setItem("access_token", "isolated-session-a"),
  )
  let secondAccount = false
  let releaseQuotes: () => void = () => undefined
  const quotesGate = new Promise<void>((resolve) => {
    releaseQuotes = resolve
  })
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === "/api/v1/users/me")
      return route.fulfill({
        json: {
          id: secondAccount
            ? "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
            : "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
          full_name: secondAccount ? "Khách B" : "Khách A",
          email: "test@example.test",
          role: "customer",
          is_active: true,
          is_superuser: false,
        },
      })
    if (path === "/api/v1/login/access-token")
      return route.fulfill({
        json: { access_token: "isolated-session-b", token_type: "bearer" },
      })
    if (path === "/api/v1/quotes") {
      if (secondAccount) {
        await quotesGate
        return route.fulfill({ json: { data: [], count: 0 } })
      }
      return route.fulfill({
        json: {
          data: [
            {
              id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
              quote_number: "QUO-PRIVATE-A",
              status: "ACCEPTED",
              total_amount: 100000,
              items: [],
            },
          ],
          count: 1,
        },
      })
    }
    return route.fulfill({ json: { data: [], count: 0 } })
  })
  await page.goto("/quotes")
  await expect(page.getByText("QUO-PRIVATE-A", { exact: true })).toBeVisible()
  await page.getByTestId("user-menu").click()
  await page.getByRole("menuitem", { name: "Đăng xuất" }).click()
  await expect(page).toHaveURL(/\/login$/)
  secondAccount = true
  await page.getByTestId("email-input").fill("second@example.test")
  await page
    .getByTestId("password-input")
    .fill(`test-only-${crypto.randomUUID()}`)
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click()
  await expect(page).toHaveURL(/\/app$/)
  await page.getByRole("link", { name: "Báo giá", exact: true }).click()
  await expect(page).toHaveURL(/\/quotes$/)
  try {
    await expect(page.getByText("QUO-PRIVATE-A", { exact: true })).toHaveCount(
      0,
    )
  } finally {
    releaseQuotes()
  }
})

test("đăng ký gửi đúng dữ liệu rồi chuyển đến đăng nhập", async ({ page }) => {
  await page.route("**/api/v1/users/signup", async (route) => {
    expect(route.request().postDataJSON()).toMatchObject({
      email: "customer@example.test",
      full_name: "Khách kiểm thử",
    })
    await route.fulfill({
      json: {
        id: crypto.randomUUID(),
        email: "customer@example.test",
        role: "customer",
        is_active: true,
      },
    })
  })
  await page.goto("/signup")
  const password = `test-only-${crypto.randomUUID()}`
  await page.getByTestId("full-name-input").fill("Khách kiểm thử")
  await page.getByTestId("email-input").fill("customer@example.test")
  await page.getByTestId("password-input").fill(password)
  await page.getByTestId("confirm-password-input").fill(password)
  const response = page.waitForResponse(
    (r) => r.url().includes("/users/signup") && r.request().method() === "POST",
  )
  await page.getByRole("button", { name: "Sign Up", exact: true }).click()
  expect((await response).status()).toBe(200)
  await expect(page).toHaveURL(/\/login$/)
})

test("hồ sơ giữ form khi API lỗi và cập nhật khi thử lại", async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem("access_token", "isolated-test-session"),
  )
  const user = {
    id: crypto.randomUUID(),
    email: "customer@example.test",
    full_name: "Tên ban đầu",
    role: "customer",
    is_active: true,
    is_superuser: false,
  }
  let attempts = 0
  await page.route("**/api/v1/users/me", async (route) => {
    if (route.request().method() === "PATCH") {
      attempts++
      if (attempts === 1)
        return route.fulfill({
          status: 500,
          json: { detail: "Internal error" },
        })
      expect(route.request().postDataJSON()).toMatchObject({
        full_name: "Tên cập nhật",
      })
      Object.assign(user, route.request().postDataJSON())
    }
    await route.fulfill({ json: user })
  })
  await page.goto("/settings")
  await page.getByRole("button", { name: "Edit", exact: true }).click()
  await page.getByLabel("Full name", { exact: true }).fill("Tên cập nhật")
  await page.getByRole("button", { name: "Save", exact: true }).click()
  await expect(page.getByLabel("Full name", { exact: true })).toHaveValue(
    "Tên cập nhật",
  )
  await expect(
    page.getByRole("button", { name: "Save", exact: true }),
  ).toBeEnabled()
  await page.getByRole("button", { name: "Save", exact: true }).click()
  await expect(page.getByText("User updated successfully")).toBeVisible()
  await expect(
    page.locator("form").getByText("Tên cập nhật", { exact: true }),
  ).toBeVisible()
  expect(attempts).toBe(2)
})

test("gửi yêu cầu khôi phục và đặt mật khẩu mới qua contract API", async ({
  page,
}) => {
  await page.route("**/api/v1/password-recovery/*", (route) =>
    route.fulfill({ json: { message: "If registered, email sent" } }),
  )
  await page.route("**/api/v1/reset-password/", async (route) => {
    expect(route.request().postDataJSON()).toMatchObject({
      token: "test-only-reset-link",
    })
    await route.fulfill({ json: { message: "Password updated successfully" } })
  })
  await page.goto("/recover-password")
  await page.getByTestId("email-input").fill("customer@example.test")
  await page.getByRole("button", { name: "Continue", exact: true }).click()
  await expect(
    page.getByText("Password recovery email sent successfully"),
  ).toBeVisible()
  await page.goto("/reset-password?token=test-only-reset-link")
  const password = `test-only-${crypto.randomUUID()}`
  await page.getByTestId("new-password-input").fill(password)
  await page.getByTestId("confirm-password-input").fill(password)
  await page
    .getByRole("button", { name: "Reset Password", exact: true })
    .click()
  await expect(page).toHaveURL(/\/login$/)
})
