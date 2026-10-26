import { test, expect, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import AxeBuilder from '@axe-core/playwright';

test.beforeEach(async ({ page }) => {
  await page.clock.install({ time: new Date('2026-10-25T12:00:00Z') });
});

async function registerLogin(page: Page) {
  const email = `browser-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;
  await page.goto('/');
  await page
    .getByRole('button', { name: 'Create account', exact: true })
    .click();
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page
    .getByLabel('Password', { exact: true })
    .fill('safe browser password 123');
  await page
    .getByRole('button', { name: 'Create account', exact: true })
    .click();
  await expect(page.getByRole('status')).toContainText('verification email');
  const token = execFileSync(
    process.env.TASKTRACK_PYTHON || '.venv/Scripts/python.exe',
    ['tests/e2e/mailbox.py', email],
    { encoding: 'utf8', env: { ...process.env, PYTHONPATH: 'src/backend' } },
  ).trim();
  await page.goto(`/#verify=${token}`);
  await page.reload();
  await page.getByRole('button', { name: 'Verify email', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Email verified');
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page
    .getByLabel('Password', { exact: true })
    .fill('safe browser password 123');
  await page.getByRole('button', { name: 'Log in', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'Your day, a little clearer.' }),
  ).toBeVisible();
  return email;
}

async function list(page: Page) {
  await page.getByRole('button', { name: 'Create list', exact: true }).click();
  await page.getByLabel('Name', { exact: true }).fill('School');
  await page.getByRole('button', { name: 'Save list', exact: true }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
}

test('register, verify, create, edit, filter, complete, reload, cancel delete and restore', async ({
  page,
}, info) => {
  const email = await registerLogin(page);
  await list(page);
  await page.getByRole('button', { name: 'New task', exact: true }).click();
  await page.getByLabel('Title', { exact: true }).fill('Finish assignment');
  await page
    .getByLabel('Description', { exact: true })
    .fill('Check persistence');
  await page
    .getByLabel('Due date (optional)', { exact: true })
    .fill('2026-10-25');
  await page.getByLabel('Priority', { exact: true }).selectOption('HIGH');
  await page
    .getByRole('button', { name: '+ Add checklist item', exact: true })
    .click();
  await page
    .getByLabel('Checklist item 1', { exact: true })
    .fill('Review requirements');
  await page.getByRole('button', { name: 'Save task', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Finish assignment', exact: true }),
  ).toBeVisible();
  await page
    .getByRole('button', { name: 'Finish assignment', exact: true })
    .click();
  await page
    .getByLabel('Title', { exact: true })
    .fill('Finish edited assignment');
  await page.getByLabel('Complete checklist item 1').check();
  await page.getByLabel('Status', { exact: true }).selectOption('IN_PROGRESS');
  await page.getByRole('button', { name: 'Save task', exact: true }).click();
  await page
    .getByLabel('Filter status', { exact: true })
    .selectOption('IN_PROGRESS');
  await expect(
    page.getByRole('button', { name: 'Finish edited assignment', exact: true }),
  ).toBeVisible();
  await page
    .getByRole('button', { name: 'Reset filters', exact: true })
    .click();
  await page
    .getByRole('button', {
      name: 'Complete Finish edited assignment',
      exact: true,
    })
    .click();
  await expect(
    page.getByRole('button', {
      name: 'Reopen Finish edited assignment',
      exact: true,
    }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole('button', {
      name: 'Reopen Finish edited assignment',
      exact: true,
    }),
  ).toBeVisible();
  mkdirSync('docs/evidence/screenshots', { recursive: true });
  await page.screenshot({
    path: `docs/evidence/screenshots/${info.project.name}-saved-workflow.png`,
    fullPage: true,
  });
  await page
    .getByRole('button', {
      name: 'Delete Finish edited assignment',
      exact: true,
    })
    .click();
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Finish edited assignment', exact: true }),
  ).toBeVisible();
  await page
    .getByRole('button', {
      name: 'Delete Finish edited assignment',
      exact: true,
    })
    .click();
  await page.getByRole('button', { name: 'Confirm', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Finish edited assignment', exact: true }),
  ).toHaveCount(0);
  await page.getByRole('button', { name: 'Trash', exact: true }).click();
  await page.getByRole('button', { name: 'Restore', exact: true }).click();
  await page.getByRole('button', { name: 'My tasks', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Finish edited assignment', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Log out', exact: true }).click();
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page
    .getByLabel('Password', { exact: true })
    .fill('safe browser password 123');
  await page.getByRole('button', { name: 'Log in', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Finish edited assignment', exact: true }),
  ).toBeVisible();
  await page
    .getByRole('button', { name: 'Finish edited assignment', exact: true })
    .click();
  await expect(page.getByLabel('Description', { exact: true })).toHaveValue(
    'Check persistence',
  );
  await expect(page.getByLabel('Complete checklist item 1')).toBeChecked();
});

test('responsive controls and automated accessibility at 360, 768 and 1920 pixels', async ({
  page,
}, info) => {
  await registerLogin(page);
  await list(page);
  for (const width of [360, 768, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await expect(
      page.getByRole('button', { name: 'Create list', exact: true }),
    ).toBeVisible();
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
      .analyze();
    expect(results.violations).toEqual([]);
    await page.screenshot({
      path: `docs/evidence/screenshots/${info.project.name}-${width}px.png`,
      fullPage: true,
    });
  }
  await page.getByRole('button', { name: 'New task', exact: true }).click();
  await page.getByLabel('Title', { exact: true }).fill('');
  await page.getByRole('button', { name: 'Save task', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  expect(
    await page
      .getByLabel('Title', { exact: true })
      .evaluate((input: HTMLInputElement) => input.validity.valueMissing),
  ).toBe(true);
  const dialog = await new AxeBuilder({ page }).include('dialog').analyze();
  expect(dialog.violations).toEqual([]);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('tags, bulk actions, calendar, schedules, reports, preferences and import/export', async ({
  page,
}, info) => {
  await registerLogin(page);
  await list(page);
  await page.getByRole('button', { name: 'Create tag', exact: true }).click();
  await page.getByLabel('Name', { exact: true }).fill('Exam');
  await page.getByRole('button', { name: 'Save tag', exact: true }).click();
  await page.getByRole('button', { name: 'New task', exact: true }).click();
  await page.getByLabel('Title', { exact: true }).fill('Organized assignment');
  await page
    .getByLabel('Due date (optional)', { exact: true })
    .fill('2026-10-25');
  await page.getByLabel('Exam', { exact: true }).check();
  await page.getByRole('button', { name: 'Save task', exact: true }).click();
  await page.getByLabel('Select Organized assignment', { exact: true }).check();
  await page
    .getByRole('button', { name: 'Complete selected', exact: true })
    .click();
  await expect(
    page.getByRole('button', {
      name: 'Reopen Organized assignment',
      exact: true,
    }),
  ).toBeVisible();
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.getByRole('button', { name: 'Calendar', exact: true }).click();
  await page
    .getByRole('button', { name: 'Organized assignment', exact: true })
    .click();
  await page
    .getByLabel('First generated date', { exact: true })
    .fill('2026-11-01');
  await page
    .getByLabel('End date (optional)', { exact: true })
    .fill('2026-11-30');
  await page
    .getByRole('button', { name: 'Save recurrence', exact: true })
    .click();
  await expect(page.getByText(/Repeats weekly/)).toBeVisible();
  await page.getByLabel(/Reminder time/).fill('2026-11-02T09:00:00');
  await page
    .getByRole('button', { name: 'Schedule reminder', exact: true })
    .click();
  await expect(page.getByText(/Scheduled/).first()).toBeVisible();
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await page.getByRole('button', { name: 'Reports', exact: true }).click();
  await expect(
    page.getByText('tasks completed', { exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Settings', exact: true }).click();
  await page
    .getByLabel('Timezone (IANA name)', { exact: true })
    .fill('America/New_York');
  await page
    .getByRole('button', { name: 'Save preferences', exact: true })
    .click();
  await expect(page.getByRole('status')).toContainText('Settings saved');
  await page
    .getByRole('button', { name: 'Import & export', exact: true })
    .click();
  const downloadPromise = page.waitForEvent('download');
  const queued = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/exports') &&
      response.request().method() === 'POST',
  );
  await page
    .getByRole('button', { name: 'Download export', exact: true })
    .click();
  await queued;
  execFileSync(
    process.env.TASKTRACK_PYTHON || '.venv/Scripts/python.exe',
    ['tests/e2e/mailbox.py', '--exports'],
    { env: { ...process.env, PYTHONPATH: 'src/backend' } },
  );
  const download = await downloadPromise;
  const path = info.outputPath('export.json');
  await download.saveAs(path);
  await page
    .getByLabel('Choose JSON export', { exact: true })
    .setInputFiles(path);
  await expect(
    page.getByText('1 lists · 1 tasks · 1 tags', { exact: true }),
  ).toBeVisible();
  await page
    .getByRole('button', { name: 'Confirm import', exact: true })
    .click();
  await expect(page.getByRole('status')).toContainText('Imported 1 tasks');
  await page.getByRole('button', { name: 'My tasks', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Organized assignment', exact: true }),
  ).toHaveCount(2);
  await page.screenshot({
    path: `docs/evidence/screenshots/${info.project.name}-organization.png`,
    fullPage: true,
  });
});
