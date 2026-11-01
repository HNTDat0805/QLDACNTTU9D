import { readdir, readFile, writeFile } from "node:fs/promises"
import path from "node:path"

// A mechanical generator step: preserve every token, normalize trailing spaces only.
const generatedRoot = path.resolve("src/client")
if (path.resolve(process.argv[2] ?? "") !== generatedRoot) {
  throw new Error("Only the generated API client directory can be normalized")
}
async function normalize(directory: string): Promise<void> {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const file = path.join(directory, entry.name)
    if (entry.isDirectory()) await normalize(file)
    else if (entry.name.endsWith(".ts")) {
      const original = await readFile(file, "utf8")
      const normalized = original.replace(/[\t ]+$/gm, "")
      if (normalized !== original) await writeFile(file, normalized)
    }
  }
}
await normalize(generatedRoot)
