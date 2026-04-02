import { test, expect } from '@playwright/test';
import { LoginPage } from './pom/LoginPage';
import { SiteOperationsPage } from './pom/SiteOperationsPage';
import { DashboardPage } from './pom/DashboardPage';

test.describe('Site Operations Lifecycle', () => {
    let loginPage: LoginPage;
    let siteOpsPage: SiteOperationsPage;
    let dashboardPage: DashboardPage;

    test.beforeEach(async ({ page }) => {
        loginPage = new LoginPage(page);
        siteOpsPage = new SiteOperationsPage(page);
        dashboardPage = new DashboardPage(page);

        await loginPage.goto();
        // Using Amit's credentials for Site Operations review
        await loginPage.login('amit@thirdangleconcept.com', 'Admin@1234');
        await loginPage.expectDashboard();

        // Switch context to Majorda Villa
        await dashboardPage.selectProject('Majorda Villa - Civil Works');
    });

    test('DPR: Admin should be able to review daily progress reports', async ({ page }) => {
        await siteOpsPage.goto();
        await siteOpsPage.switchTab('dprs');

        // Seed data verification (if exists) or just verify grid loads
        await expect(siteOpsPage.siteOperationsGrid).toBeVisible({ timeout: 20000 });

        // Search for a common keyword if known, otherwise just check rows exist
        const rows = page.locator('.ag-center-cols-container .ag-row');
        await expect(rows.first()).toBeVisible({ timeout: 15000 });
    });

    test('ATTENDANCE: Admin should be able to monitor worker attendance logs', async ({ page }) => {
        await siteOpsPage.goto();
        await siteOpsPage.switchTab('attendance');

        await expect(siteOpsPage.siteOperationsGrid).toBeVisible({ timeout: 20000 });

        // Verify verification button is present in at least one row (if any are unverified)
        // Or just verify row visibility
        const rows = page.locator('.ag-center-cols-container .ag-row');
        await expect(rows.first()).toBeVisible({ timeout: 15000 });
    });

    test('FUNDS: Admin should be able to view site liquidity and petty cash labels', async ({ page }) => {
        await siteOpsPage.goto();
        await siteOpsPage.switchTab('funds');

        // Verify Site Funds content
        await expect(page.getByText(/Recent Petty Cash Transactions|Cash in Hand/i).first()).toBeVisible({ timeout: 20000 });
        await expect(siteOpsPage.siteOperationsGrid).toBeVisible();
    });
});
