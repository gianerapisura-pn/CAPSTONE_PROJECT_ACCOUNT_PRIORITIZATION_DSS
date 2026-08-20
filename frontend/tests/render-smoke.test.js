const fs = require("fs");
const path = require("path");

const requiredFiles = [
  "app/page.tsx",
  "app/import/page.tsx",
  "app/accounts/page.tsx",
  "app/analytics/page.tsx",
  "app/reports/page.tsx",
  "components/account-priority-table.tsx",
  "components/import-panel.tsx"
];

for (const file of requiredFiles) {
  const full = path.join(__dirname, "..", file);
  if (!fs.existsSync(full)) {
    throw new Error(`Missing frontend file: ${file}`);
  }
}
