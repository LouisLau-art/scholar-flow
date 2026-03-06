import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const packageJsonPath = resolve(process.cwd(), "package.json");
const packageJson = JSON.parse(readFileSync(packageJsonPath, "utf8"));

const nextVersion = packageJson.dependencies?.next;
const reactVersion = packageJson.dependencies?.react;
const reactDomVersion = packageJson.dependencies?.["react-dom"];
const eslintConfigNextVersion = packageJson.devDependencies?.["eslint-config-next"];
const eslintVersion = packageJson.devDependencies?.eslint;

function extractMajor(version, label) {
  if (!version || typeof version !== "string") {
    throw new Error(`缺少 ${label} 版本声明`);
  }
  const match = version.match(/(\d+)/);
  if (!match) {
    throw new Error(`无法解析 ${label} 版本: ${version}`);
  }
  return Number.parseInt(match[1], 10);
}

const nextMajor = extractMajor(nextVersion, "next");
const reactMajor = extractMajor(reactVersion, "react");
const reactDomMajor = extractMajor(reactDomVersion, "react-dom");
const eslintConfigNextMajor = extractMajor(
  eslintConfigNextVersion,
  "eslint-config-next",
);
const eslintMajor = extractMajor(eslintVersion, "eslint");

const errors = [];

if (nextMajor !== eslintConfigNextMajor) {
  errors.push(
    `next(${nextVersion}) 与 eslint-config-next(${eslintConfigNextVersion}) 主版本不一致`,
  );
}

if (nextMajor >= 15 && reactMajor < 19) {
  errors.push(`next ${nextVersion} 需要 React 19+，当前 react=${reactVersion}`);
}

if (nextMajor >= 15 && reactDomMajor < 19) {
  errors.push(
    `next ${nextVersion} 需要 React DOM 19+，当前 react-dom=${reactDomVersion}`,
  );
}

if (eslintConfigNextMajor >= 16 && eslintMajor < 9) {
  errors.push(
    `eslint-config-next ${eslintConfigNextVersion} 需要 eslint 9+，当前 eslint=${eslintVersion}`,
  );
}

if (errors.length > 0) {
  console.error("Next toolchain 对齐检查失败:");
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  process.exit(1);
}

console.log("Next toolchain 对齐检查通过:");
console.log(`- next=${nextVersion}`);
console.log(`- react=${reactVersion}`);
console.log(`- react-dom=${reactDomVersion}`);
console.log(`- eslint-config-next=${eslintConfigNextVersion}`);
console.log(`- eslint=${eslintVersion}`);
