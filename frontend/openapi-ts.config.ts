import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./openapi.json",
  output: {
    path: "./src/client",
    postProcess: [
      { command: "bun", args: ["scripts/normalize-generated.ts", "{{path}}"] },
    ],
  },

  plugins: [
    { name: "@hey-api/client-axios", throwOnError: true },
    { name: "@hey-api/typescript", case: "preserve" },
    {
      name: "@hey-api/sdk",
      operations: {
        // NOTE: this doesn't allow tree-shaking
        strategy: "byTags",
        methods: "static",
        containerName: "{{name}}Service",
        methodName: (name: string): string => name.replace(/^[^-]*-/, ""),
      },
    },
  ],
})
