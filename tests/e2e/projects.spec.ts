import { test, expect } from '@playwright/test';
import { LoginPage } from './pom/LoginPage';
import { ProjectPage } from './pom/ProjectPage';
import { DashboardPage } from './pom/DashboardPage';

test.describe('Project Lifecycle & Portfolio Management', () => {
    let loginPage: LoginPage;
    let projectPage: ProjectPage;
    let dashboardPage: DashboardPage;

    test.beforeEach(async ({ page }) => {
        page.on('console', msg => console.log(`BROWSER [${msg.type()}]: ${msg.text()}`));
        page.on('pageerror', err => console.log(`BROWSER ERROR: ${err.message}`));

        loginPage = new LoginPage(page);
        projectPage = new ProjectPage(page);
        dashboardPage = new DashboardPage(page);

        await loginPage.goto();
        // Using Amit's credentials as primary admin for lifecycle tests
        await loginPage.login('amit@thirdangleconcept.com', 'Admin@1234');
        await loginPage.expectDashboard();
    });

    test('PORTFOLIO: Admin should be able to create a new strategic project', async ({ page }) => {
        const projectName = `E2E-PROJ-${Date.now()}`;
        const projectCode = `TP-${Math.floor(Math.random() * 1000)}`;

        await projectPage.goto();
        await projectPage.createProject(projectName, projectCode, '123 E2E Test Lane, Digital City');

        // Verify it appeared in the registry
        await projectPage.searchAndVerify(projectName);
    });

    test('DASHBOARD: Admin should be able to switch active project context', async ({ page }) => {
        await dashboardPage.goto();
        const targetProject = 'Majorda Villa - Civil Works';

        await dashboardPage.selectProject(targetProject);
        await dashboardPage.expectActiveProject(targetProject);

        await expect(page.getByText('Portfolio Value')).toBeVisible();
    });

    test('INTELLIGENCE: Admin should be able to navigate to project enterprise view', async ({ page }) => {
        const targetProject = 'Majorda Villa - Civil Works';

        await projectPage.goto();
        // Ag-grid loading behavior
        await page.waitForTimeout(2000);
        await projectPage.searchAndVerify(targetProject);
        // Start waiting for BOTH key responses
        const projectResponse = page.waitForResponse(resp => resp.url().includes('/api/v1/projects/') && !resp.url().includes('financials') && resp.status() === 200, { timeout: 30000 });
        const financialsResponse = page.waitForResponse(resp => resp.url().includes('/financials') && resp.status() === 200, { timeout: 30000 });

        await projectPage.navigateToProjectDetails(targetProject);

        // Wait for URL change
        await page.waitForURL(/.*\/admin\/projects\/.*/, { timeout: 20000 });

        // Ensure both data sets are loaded
        await Promise.all([projectResponse, financialsResponse]);

        // Hardening: wait for the specific project name to appear in the dashboard header or a known project detail element
        // This ensures the async data fetch has completed
        // Hardening: wait for the project name to appear on the page
        await expect(page.getByText(targetProject).first()).toBeVisible({ timeout: 25000 });

        // Verify that financial grid loaded data rows
        await expect(page.locator('.ag-row').first()).toBeVisible({ timeout: 20000 });

        // Verify that financial cards loaded and show meaningful values
        // We look for digits followed by decimals to be currency-agnostic but data-positive
        await expect(page.locator('.text-3xl').filter({ hasText: /[1-9]/ }).first()).toBeVisible({ timeout: 15000 });

        // Also verify visible project core metrics to ensure full load
        await expect(page.getByText(/Category-wise Financials|Total Budget/i).first()).toBeVisible({ timeout: 15000 });
    });
});
