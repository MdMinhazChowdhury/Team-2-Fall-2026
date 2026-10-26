import assert from 'node:assert/strict';
import process from 'node:process';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { chromium } from '@playwright/test';

// Run only after stopping and relaunching the API against tasktrack_e2e.
const state = JSON.parse(
  execFileSync(
    process.env.TASKTRACK_PYTHON || '.venv/Scripts/python.exe',
    ['tests/e2e/mailbox.py', '--restart-state'],
    { encoding: 'utf8', env: { ...process.env, PYTHONPATH: 'src/backend' } },
  ),
);
const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:5173');
  await page.getByLabel('Email', { exact: true }).fill(state.email);
  await page
    .getByLabel('Password', { exact: true })
    .fill('safe browser password 123');
  await page.getByRole('button', { name: 'Log in', exact: true }).click();
  await page.getByRole('button', { name: state.title, exact: true }).click();
  assert.equal(
    await page.getByLabel('Description', { exact: true }).inputValue(),
    'Check persistence',
  );
  assert.equal(
    await page.getByLabel('Due date (optional)', { exact: true }).inputValue(),
    '2026-10-25',
  );
  assert.equal(
    await page.getByLabel('Status', { exact: true }).inputValue(),
    'COMPLETED',
  );
  assert.equal(
    await page.getByLabel('Complete checklist item 1').isChecked(),
    true,
  );
  await page.screenshot({
    path: 'docs/evidence/screenshots/api-restarted.png',
    fullPage: true,
  });
  writeFileSync(
    'docs/evidence/api-restart.json',
    JSON.stringify(
      {
        recorded_at: new Date().toISOString(),
        passed: true,
        browser: await browser.version(),
        verified: [
          'login after API process restart',
          'saved title',
          'saved description',
          'saved deadline',
          'completed status',
          'completed checklist',
        ],
      },
      null,
      2,
    ),
  );
} finally {
  await browser.close();
}
