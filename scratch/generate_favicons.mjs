import { chromium } from "playwright"
import fs from "fs"
import path from "path"

async function generate() {
  const browser = await chromium.launch({ channel: "msedge" })
  const page = await browser.newPage()
  
  const svgPath = path.resolve("frontend/public/favicon.svg")
  const svgContent = fs.readFileSync(svgPath, "utf-8")
  
  const sizes = [16, 32, 48, 64, 128, 192, 512]
  
  for (const size of sizes) {
    await page.setViewportSize({ width: size, height: size })
    await page.setContent(`
      <!DOCTYPE html>
      <html>
        <head>
          <style>
            * { margin: 0; padding: 0; }
            html, body { width: ${size}px; height: ${size}px; overflow: hidden; background: transparent; }
            svg { width: ${size}px; height: ${size}px; display: block; }
          </style>
        </head>
        <body>${svgContent}</body>
      </html>
    `)
    
    const buf = await page.screenshot({ omitBackground: true, type: "png" })
    fs.writeFileSync(`frontend/public/favicon-${size}.png`, buf)
    console.log(`Generated favicon-${size}.png (${size}x${size})`)
  }
  
  // Also copy default favicon.png (64x64) and apple-touch-icon (192x192)
  fs.copyFileSync("frontend/public/favicon-64.png", "frontend/public/favicon.png")
  fs.copyFileSync("frontend/public/favicon-64.png", "frontend/public/assets/images/favicon.png")
  fs.copyFileSync("frontend/public/favicon-128.png", "frontend/public/assets/images/favicon-128.png")
  
  await browser.close()
  console.log("Playwright PNG generation done!")
}

generate().catch(console.error)
