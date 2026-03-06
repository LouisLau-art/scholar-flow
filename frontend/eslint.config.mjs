import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

export default defineConfig([
  ...nextVitals,
  globalIgnores([
    "node_modules/**",
    ".next/**",
    "out/**",
    "build/**",
    "dist/**",
    "coverage/**",
    "next-env.d.ts",
  ]),
]);
