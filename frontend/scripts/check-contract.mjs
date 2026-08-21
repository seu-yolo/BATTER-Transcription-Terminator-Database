import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const requiredFiles = [
  "package.json",
  "next.config.mjs",
  ".env.example",
  "lib/api.ts",
  "app/page.tsx",
  "app/sources/page.tsx",
  "app/sources/[sourceId]/page.tsx",
  "app/assemblies/page.tsx",
  "app/assemblies/[assemblyId]/page.tsx",
  "app/endpoints/[endId]/page.tsx",
  "app/augmentation/page.tsx",
  "app/explore/page.tsx",
];

for (const relative of requiredFiles) {
  if (!existsSync(resolve(frontend, relative))) {
    throw new Error(`missing required frontend file: ${relative}`);
  }
}

const read = (relative) => readFileSync(resolve(frontend, relative), "utf8");
const home = read("app/page.tsx");
const api = read("lib/api.ts");
const config = read("next.config.mjs");
const source = read("app/sources/[sourceId]/page.tsx");
const explore = read("app/explore/page.tsx");
const assertions = [
  [home, "getStats", "home loads dynamic release statistics"],
  [home, "Search by accession", "home has accession search entry"],
  [home, "Data augmentation", "home has augmentation entry"],
  [api, "/api/v1/stats", "API wrapper includes stats"],
  [api, "BTED_API_ORIGIN", "API origin is environment controlled"],
  [config, "BTED_API_ORIGIN", "rewrite uses API origin"],
  [config, "localhost", "rewrite must not hard-code localhost"],
  [source, "Metadata audit only", "audit-only source boundary is visible"],
  [source, "Download endpoint table", "source download entry exists"],
  [explore, "Filter records", "endpoint filters are server-side"],
  [explore, "Assembly view", "endpoint context entry exists"],
];
for (const [content, needle, description] of assertions) {
  if (needle === "localhost" ? content.includes(needle) : !content.includes(needle)) {
    throw new Error(`contract assertion failed: ${description}`);
  }
}

console.log(`BTED frontend contract: PASS (${requiredFiles.length} route/config files checked)`);
