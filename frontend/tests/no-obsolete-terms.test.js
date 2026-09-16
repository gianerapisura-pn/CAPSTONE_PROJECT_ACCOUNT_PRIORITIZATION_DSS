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
  "Stronger Account Pattern",
  "Normalized RFM",
  "CRITIC RFM weight",
  "Baseline RFM weight",
  "normalized_rfm",
  "rfm_contribution",
  "actual_rfm_weight",
  "Reports & Export",
  "Supabase authenticated",
  "Power BI cannot clean data",
  "Power BI cannot accept future data"
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

const sourceRoots = ["app", "components", "lib", "types"].map((dir) => path.join(__dirname, "..", dir));
const text = sourceRoots.flatMap(walk)
  .filter((file) => [".ts", ".tsx", ".css"].includes(path.extname(file)))
  .map((file) => fs.readFileSync(file, "utf8"))
  .join("\n");

for (const term of forbidden) {
  if (text.includes(term)) {
    throw new Error(`Obsolete methodology term found: ${term}`);
  }
}

const root = path.join(__dirname, "..");
const details = fs.readFileSync(path.join(root, "app", "(protected)", "accounts", "[accountKey]", "page.tsx"), "utf8");
for (const term of ["Normalized Recency", "Normalized Frequency", "Normalized Monetary", "Normalized Settlement", "Recency weight / contribution", "Frequency weight / contribution", "Monetary weight / contribution", "Settlement weight / contribution"]) {
  if (!details.includes(term)) throw new Error(`Account Details is missing: ${term}`);
}
for (const relative of [
  ["app", "(protected)", "analytics", "sensitivity", "page.tsx"],
  ["app", "(protected)", "runs", "page.tsx"],
]) {
  const page = fs.readFileSync(path.join(root, ...relative), "utf8");
  for (const criterion of ["recency", "frequency", "monetary", "settlement"]) {
    if (!page.toLowerCase().includes(criterion)) throw new Error(`${relative.join("/")} is missing ${criterion} weight context`);
  }
}