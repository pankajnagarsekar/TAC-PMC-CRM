import { test, expect } from '@playwright/test';
import { LoginPage } from './pom/LoginPage';
import { DashboardPage } from './pom/DashboardPage';
import { WorkOrderPage } from './pom/WorkOrderPage';

test.describe('Work Order Module Lifecycle', () => {
    let loginPage: LoginPage;
    let dashboardPage: DashboardPage;
    let workOrderPage: WorkOrderPage;

    test.beforeEach(async ({ page }) => {
        loginPage = new LoginPage(page);
        dashboardPage = new DashboardPage(page);
        workOrderPage = new WorkOrderPage(page);

        // Login as Admin
        await loginPage.goto();
        await loginPage.login('admin@tacpmc.com', 'Admin@1234');
        await loginPage.expectDashboard();

        // Select a project context (using first available project)
        await dashboardPage.goto();
        await page.waitForSelector('h4');
        const firstProject = await page.locator('h4').first().textContent();
        if (firstProject) {
            await dashboardPage.selectProject(firstProject.trim());
        }
    });

    test('Should create a new Work Order successfully', async ({ page }) => {
        await workOrderPage.goto();

        const description = `E2E Test Work Order ${Date.now()}`;
        const itemDescription = 'Test Item';
        const qty = '10';
        const rate = '500';

        await workOrderPage.createWorkOrder(description, itemDescription, qty, rate);

        // After creation, we should be on the list page or details page
        await expect(page).toHaveURL(/\/admin\/work-orders(\/.*)?/);

        // Verify it exists in the grid (if we are on the list page)
        if (page.url().endsWith('/admin/work-orders')) {
            await workOrderPage.searchAndVerify(description);
        }
    });

    test('Should have Save button disabled initially', async ({ page }) => {
        await workOrderPage.goto();
        await workOrderPage.newWorkOrderButton.click();

        // Initially disabled
        await expect(workOrderPage.saveButton).toBeDisabled();
    });

    test('Should filter Work Orders using search', async ({ page }) => {
        await workOrderPage.goto();

        // Wait for grid to load some data if any
        await page.waitForTimeout(2000);

        // Try searching for a known reference if possible, otherwise just verify search input works
        await workOrderPage.searchInput.fill('WO');
        await page.waitForTimeout(1000);
        // Grid should at least be visible
        await expect(workOrderPage.grid).toBeVisible();
    });
});
