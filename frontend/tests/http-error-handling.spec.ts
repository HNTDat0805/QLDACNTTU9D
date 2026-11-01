import { expect, type Page, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })
test.setTimeout(30_000)

const setAccessTokenBeforeNavigation = async (page: Page) => {
  await page.goto("/login")
  await page.evaluate(() => {
    localStorage.setItem("access_token", "expired-or-test-token")
  })
}

const mockCurrentUserError = async (page: Page, status: number) => {
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({
      body: JSON.stringify({ detail: "Request failed" }),
      contentType: "application/json",
      status,
    }),
  )
}

const submitLogin = async (page: Page) => {
  await page.goto("/login")
  await page.getByTestId("email-input").fill("student@example.com")
  await page.getByTestId("password-input").fill("valid-password")
  await page.getByRole("button", { name: "Đăng nhập" }).click()
}

test("401 expired token clears the token and redirects once", async ({
  page,
}) => {
  await setAccessTokenBeforeNavigation(page)
  await mockCurrentUserError(page, 401)

  await page.goto("/settings")

  await expect(page).toHaveURL(/\/login$/)
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("access_token")))
    .toBeNull()
})

test("401 refreshes a valid session once and retries the request", async ({
  page,
}) => {
  await setAccessTokenBeforeNavigation(page)
  await page.evaluate(() => {
    localStorage.setItem("refresh_token", "valid-refresh-token")
  })

  let currentUserRequests = 0
  let refreshRequests = 0
  await page.route("**/api/v1/users/me", (route) => {
    currentUserRequests += 1
    if (currentUserRequests === 1) {
      return route.fulfill({
        body: JSON.stringify({ detail: "Expired access token" }),
        contentType: "application/json",
        status: 401,
      })
    }

    return route.fulfill({
      body: JSON.stringify({
        email: "customer@example.com",
        full_name: "FixCare Customer",
        id: "00000000-0000-0000-0000-000000000001",
        is_active: true,
        is_superuser: false,
        role: "customer",
      }),
      contentType: "application/json",
      status: 200,
    })
  })
  await page.route("**/api/v1/login/refresh-token", (route) => {
    refreshRequests += 1
    return route.fulfill({
      body: JSON.stringify({
        access_token: "refreshed-access-token",
        refresh_token: "rotated-refresh-token",
        token_type: "bearer",
      }),
      contentType: "application/json",
      status: 200,
    })
  })

  await page.goto("/settings")

  await expect(page).toHaveURL(/\/settings$/)
  await expect(
    page.getByLabel("My profile").getByText("FixCare Customer", {
      exact: true,
    }),
  ).toBeVisible()
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("access_token")))
    .toBe("refreshed-access-token")
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("refresh_token")))
    .toBe("rotated-refresh-token")
  expect(currentUserRequests).toBeGreaterThanOrEqual(2)
  expect(refreshRequests).toBe(1)
})

test("401 invalid login keeps the login page and shows the API message", async ({
  page,
}) => {
  await page.route("**/api/v1/login/access-token", (route) =>
    route.fulfill({
      body: JSON.stringify({ detail: "Incorrect email or password" }),
      contentType: "application/json",
      status: 401,
    }),
  )

  await submitLogin(page)

  await expect(page).toHaveURL(/\/login$/)
  await expect(
    page.getByText("Incorrect email or password", { exact: true }),
  ).toBeVisible()
})

test("403 keeps the token and shows one permission message", async ({
  page,
}) => {
  await setAccessTokenBeforeNavigation(page)
  await mockCurrentUserError(page, 403)

  await page.goto("/settings")

  await expect(page).toHaveURL(/\/settings$/)
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("access_token")))
    .toBe("expired-or-test-token")
  await expect(
    page.getByText("Bạn không có quyền thực hiện thao tác này.", {
      exact: true,
    }),
  ).toHaveCount(1)
})

for (const [status, expectedMessage] of [
  [404, "Không tìm thấy dữ liệu bạn yêu cầu."],
  [500, "Máy chủ đang gặp sự cố. Vui lòng thử lại sau."],
] as const) {
  test(`${status} shows a friendly mutation error`, async ({ page }) => {
    await page.route("**/api/v1/login/access-token", (route) =>
      route.fulfill({
        body: JSON.stringify({ detail: "Internal API detail" }),
        contentType: "application/json",
        status,
      }),
    )

    await submitLogin(page)

    await expect(page.getByText(expectedMessage, { exact: true })).toBeVisible()
  })
}

test("422 shows the first FastAPI field validation message", async ({
  page,
}) => {
  await page.route("**/api/v1/login/access-token", (route) =>
    route.fulfill({
      body: JSON.stringify({
        detail: [
          {
            loc: ["body", "username"],
            msg: "Email không hợp lệ",
            type: "value_error",
          },
        ],
      }),
      contentType: "application/json",
      status: 422,
    }),
  )

  await submitLogin(page)

  await expect(
    page.getByText("username: Email không hợp lệ", { exact: true }),
  ).toBeVisible()
})

test("network error keeps the token and does not redirect", async ({
  page,
}) => {
  await setAccessTokenBeforeNavigation(page)
  await page.route("**/api/v1/users/me", (route) => route.abort("failed"))

  await page.goto("/settings")

  await expect(page).toHaveURL(/\/settings$/)
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("access_token")))
    .toBe("expired-or-test-token")
  await expect(
    page.getByText(
      "Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối và thử lại.",
      { exact: true },
    ),
  ).toHaveCount(1, { timeout: 15_000 })
})
