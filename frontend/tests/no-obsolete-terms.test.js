const fs = require("fs");
const path = require("path");

const forbidden = [
  "Settlement Behavior Score",
  "Moderate Inactivity Risk",
  "75% RFM",
  "25% Settlement",
  "60/40",
  "70/30",
  "80/20",
  "Stronger Account Pattern"
];

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory() && ["node_modules", ".next", "coverage"].includes(entry.name)) {
      return [];
    }
    return entry.isDirectory() ? walk(full) : [full];
  });
}

const text = walk(path.join(__dirname, ".."))
  .filter((file) => [".ts", ".tsx", ".css"].includes(path.extname(file)))
  .map((file) => fs.readFileSync(file, "utf8"))
  .join("\n");

for (const term of forbidden) {
  if (text.includes(term)) {
    throw new Error(`Obsolete methodology term found: ${term}`);
  }
}
