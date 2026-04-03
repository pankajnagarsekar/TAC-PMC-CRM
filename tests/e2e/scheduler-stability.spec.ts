import { test, expect } from '@playwright/test';
import { LoginPage } from './pom/LoginPage';

test.describe('Scheduler Stability & UI Parity (Phase 15)', () => {
    let loginPage: LoginPage;

    test.beforeEach(async ({ page }) => {
        loginPage = new LoginPage(page);
        await loginPage.goto();
        await loginPage.login('amit@thirdangleconcept.com', 'Admin@1234');
        await loginPage.expectDashboard();

        // Navigate to Scheduler
        await page.goto('/admin/scheduler');

        // Robust project selection
        await page.waitForTimeout(3000);
        if (await page.getByText(/No Project Selected/i).isVisible() || await page.getByRole('button', { name: /Select Project/i }).isVisible()) {
            try {
                await page.getByRole('button', { name: /Select Project/i }).click({ timeout: 5000 });
                await page.getByRole('button', { name: /Majorda Villa/i }).first().click();
                await page.waitForTimeout(2000);
            } catch (e) { }
        }

        await expect(page.getByRole('heading', { name: /Project Planner/i })).toBeVisible({ timeout: 15000 });

        // Ensure at least one task
        if (await page.getByText(/No Active Schedule/i).isVisible()) {
            await page.getByRole('button', { name: /Add First Task/i }).click();
            await expect(page.getByText(/task-1/i).first()).toBeVisible({ timeout: 15000 });
        }
    });

    test('ISSUE 4 & 5: TaskDrawer UI Parity and Logs cleanup', async ({ page }) => {
        await page.getByText(/task-1/i).first().click();
        await expect(page.getByText(/Task Drawer/i)).toBeVisible({ timeout: 10000 });
        await page.getByRole('tab', { name: /Log Registry/i }).click();
        await expect(page.getByText(/No inline logs for this task/i)).toBeVisible();
        expect(await page.getByRole('link', { name: /View/i }).getAttribute('href')).toContain('site-operations');
    });

    test('ISSUE 2 & 3: Gantt Drag Visuals', async ({ page }) => {
        await page.getByRole('button', { name: /Gantt/i }).click();
        const taskBar = page.locator('.cursor-grab, [data-task-id]').first();
        await expect(taskBar).toBeVisible({ timeout: 15000 });
        const box = await taskBar.boundingBox();
        if (box) {
            await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
            await page.mouse.down();
            await page.mouse.move(box.x + box.width / 2 + 50, box.y + box.height / 2);
            await expect(page.locator('.ring-orange-400, .ring-orange-400\\/60').first()).toBeVisible({ timeout: 5000 });
            await page.mouse.up();
        }
    });

    test('ISSUE 1 & 6: Calculation Stability', async ({ page }) => {
        await page.getByText(/task-1/i).first().click();
        const durationInput = page.getByLabel(/Duration/i);
        await expect(durationInput).toBeVisible({ timeout: 10000 });
        const newVal = (await durationInput.inputValue()) === '5' ? '10' : '5';
        await durationInput.fill(newVal);
        await durationInput.blur();
        await page.waitForTimeout(3000);
        await expect(page.getByText(/task-1/i).first()).toBeVisible();
    });
});
