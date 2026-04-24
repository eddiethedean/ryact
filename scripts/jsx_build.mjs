import fs from "node:fs";
import path from "node:path";

import { spawnSync } from "node:child_process";

function usage() {
  console.error("Usage: node scripts/jsx_build.mjs <input.tsx> --out <output.py> [--map <output.map.json>]");
  process.exit(2);
}

const args = process.argv.slice(2);
if (args.length < 1) usage();

const inputPath = args[0];
let outPath = null;
let mapPath = null;

for (let i = 1; i < args.length; i++) {
  if (args[i] === "--out") {
    outPath = args[i + 1] ?? null;
    i++;
  } else if (args[i] === "--map") {
    mapPath = args[i + 1] ?? null;
    i++;
  }
}

if (!outPath) usage();

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const transform = path.join(repoRoot, "scripts", "jsx_to_py_transform.mjs");

const proc = spawnSync("node", [transform, inputPath, "--mode", "module"], {
  cwd: repoRoot,
  encoding: "utf8",
});
if (proc.status !== 0) {
  process.stderr.write(proc.stderr ?? "");
  process.exit(proc.status ?? 1);
}

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, proc.stdout, "utf8");

if (mapPath) {
  fs.mkdirSync(path.dirname(mapPath), { recursive: true });
  // Milestone 17: emit the same mapping the module embeds.
  // Keep this intentionally small; full sourcemaps are deferred.
  const m = proc.stdout.match(/__ryact_jsx_map__\s*=\s*(\[[\s\S]*?\])\n\ndef render/);
  const mappings = m ? JSON.parse(m[1]) : [];
  fs.writeFileSync(
    mapPath,
    JSON.stringify({ input: inputPath, generated: outPath, version: 0, mappings }, null, 2) + "\n",
    "utf8"
  );
}

