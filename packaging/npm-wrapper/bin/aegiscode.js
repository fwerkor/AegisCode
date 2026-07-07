#!/usr/bin/env node
const { spawnSync } = require("node:child_process");
const result = spawnSync("python", ["-m", "aegiscode.cli", ...process.argv.slice(2)], { stdio: "inherit" });
if (result.error) {
  console.error("AegisCode Python package is required. Install it with: pipx install aegiscode");
  process.exit(1);
}
process.exit(result.status ?? 1);
