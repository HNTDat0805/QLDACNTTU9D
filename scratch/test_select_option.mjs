import { chromium } from "playwright"

async function testPlaywright() {
  const browser = await chromium.launch({ channel: "msedge" })
  const page = await browser.newPage()
  await page.setContent(`
    <div>
      <label for="rating">Số sao</label>
      <select id="rating" class="opacity-0 w-0 h-0 absolute pointer-events-none" style="opacity: 0; width: 0px; height: 0px; position: absolute;">
        <option value="5">5 sao</option>
      </select>
    </div>
  `)
  try {
    await page.getByLabel("Số sao").selectOption("5", { timeout: 2000 })
    console.log("SUCCESS!")
  } catch (e) {
    console.log("FAIL:", e.message)
  }
  await browser.close()
}

testPlaywright()

