const { test, expect } = require('@playwright/test');
const { parse } = require('csv-parse/sync');
const ExcelJS = require('exceljs');
const { createHash } = require('node:crypto');
const { readFileSync } = require('node:fs');

// These fingerprints were generated from PESLC_FINAL_QA(2).zip, not live exports.
const APPROVED = {
  ranks: '96b04b8ba654043b1b7920381ffcf4e4bc9a2299ce11b08be21a3623b93f165d',
  contributions: 'd264319782067260a6e085d42cb6212341a4cc3a2651c3a13a31472e288903ca',
};

const measures = [
  'normalized_recency', 'normalized_frequency', 'normalized_monetary',
  'normalized_settlement', 'recency_contribution', 'frequency_contribution',
  'monetary_contribution', 'settlement_contribution',
];

function digest(rows, fields) {
  const lines = rows.map(row => {
    const name = String(row.account ?? '').trim().toUpperCase();
    const values = fields.map(field => {
      if (field === 'priority_rank') return String(Number(row[field]));
      if (field === 'priority_group') return String(row[field] ?? '').trim();
      const number = Number(row[field]);
      if (!Number.isFinite(number)) throw new Error(`Missing numeric value for ${field}`);
      return number.toFixed(9);
    });
    return [name, ...values].join('|');
  });
  lines.sort((a, b) => Buffer.compare(Buffer.from(a.split('|')[0]), Buffer.from(b.split('|')[0])));
  return createHash('sha256').update(lines.join('\n'), 'utf8').digest('hex');
}

function verify(rows, fileType) {
  if (rows.length !== 84) throw new Error(`${fileType}: expected 84 historical B2B rows, received ${rows.length}`);
  const ranked = rows.filter(row => Number.isInteger(Number(row.priority_rank)) && Number(row.priority_rank) >= 1);
  if (ranked.length !== 83) throw new Error(`${fileType}: expected 83 ranked rows, received ${ranked.length}`);
  const ranks = ranked.map(row => Number(row.priority_rank));
  if (new Set(ranks).size !== 83 || Math.min(...ranks) !== 1 || Math.max(...ranks) !== 83) {
    throw new Error(`${fileType}: rank sequence is not 1 through 83`);
  }
  const groups = Object.fromEntries(['High','Medium','Low'].map(group => [group, ranked.filter(row => row.priority_group === group).length]));
  if (groups.High !== 28 || groups.Medium !== 27 || groups.Low !== 28) {
    throw new Error(`${fileType}: Priority Group counts differ from approved result`);
  }
  if (rows.some(row => String(row.analysis_reference_date) !== '2025-12-31')) {
    throw new Error(`${fileType}: analysis reference does not match 2025-12-31`);
  }
  const ranksDigest = digest(ranked, ['priority_rank','priority_group','final_priority_score']);
  const contributionsDigest = digest(ranked, measures);
  if (ranksDigest !== APPROVED.ranks || contributionsDigest !== APPROVED.contributions) {
    throw new Error(`${fileType}: full-population rank or component fingerprint differs from approved analytical ZIP`);
  }
  console.log(`qa_${fileType}_83_account_fingerprint=PASS`);
}

async function signIn(page) {
  const email = process.env.PESLC_QA_EMAIL;
  const password = process.env.PESLC_QA_PASSWORD;
  if (!email || !password) throw new Error('The approved QA secrets are required');
  await page.goto('/login?next=%2Freports');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page).toHaveURL(/\/reports(?:\?|$)/, { timeout: 45_000 });
}

async function download(page, label) {
  const pending = page.waitForEvent('download', { timeout: 60_000 });
  await page.getByRole('button', { name: label, exact: true }).click();
  return (await pending).path();
}

test('CSV and XLSX contain the approved account priorities and contributions', async ({ page }) => {
  await signIn(page);
  await expect(page.getByRole('heading', { name: 'Account Prioritization export' })).toBeVisible();
  const csvPath = await download(page, 'CSV');
  const csvRows = parse(readFileSync(csvPath, 'utf8'), {
    columns: true, bom: true, skip_empty_lines: true,
  });
  verify(csvRows, 'csv');

  const xlsxPath = await download(page, 'XLSX');
  const workbook = new ExcelJS.Workbook();
  await workbook.xlsx.readFile(xlsxPath);
  const worksheet = workbook.worksheets[0];
  if (!worksheet) throw new Error('XLSX has no worksheet');
  const headings = worksheet.getRow(1).values.slice(1).map(v => String(v));
  const xlsxRows = [];
  for (let number = 2; number <= worksheet.rowCount; number++) {
    const row = worksheet.getRow(number);
    if (!row.hasValues) continue;
    const record = {};
    headings.forEach((key, index) => { record[key] = row.getCell(index + 1).value; });
    xlsxRows.push(record);
  }
  verify(xlsxRows, 'xlsx');
});
