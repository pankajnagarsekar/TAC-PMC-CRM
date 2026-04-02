import { test, expect } from '@playwright/test';
import { LoginPage } from './pom/LoginPage';

test.describe('Authentication & Identity Flows', () => {
    let loginPage: LoginPage;

    test.beforeEach(async ({ page }) => {
        loginPage = new LoginPage(page);
        await loginPage.goto();
    });

    test('ADMIN: System should allow login with provided admin credentials (Amit)', async ({ page }) => {
        await loginPage.login('amit@thirdangleconcept.com', 'Admin@1234');
        await loginPage.expectDashboard();

        // Check for "Team Management" visibility for admin
        const teamManagement = page.getByRole('link', { name: /Team Management/i });
        await expect(teamManagement).toBeVisible();

        await loginPage.logout();
    });

    test('ADMIN: System should allow login with fallback admin credentials', async ({ page }) => {
        await loginPage.login('admin@tacpmc.com', 'Admin@1234');
        await loginPage.expectDashboard();
        await loginPage.logout();
    });

    test('CLIENT: System should allow login and redirect to dashboard', async ({ page }) => {
        await loginPage.login('client@tacpmc.com', 'Client@1234');
        await loginPage.expectDashboard();

        // Check Client restrictions: Team Management should be HIDDEN
        const teamManagement = page.getByRole('link', { name: /Team Management/i });
        await expect(teamManagement).not.toBeVisible();

        await loginPage.logout();
    });

    test('SECURITY: System should reject invalid credentials', async ({ page }) => {
        await loginPage.login('wrong@tacpmc.com', 'wrongpassword');
        await loginPage.expectError('Login failed');
    });

    test('RBAC: Supervisor should be DENIED access to web portal', async ({ page }) => {
        await loginPage.login('supervisor@tacpmc.com', 'Supervisor@1234');
        await loginPage.expectError('Access denied. This portal is for Admin and Client users only.');
        await expect(page).toHaveURL(/.*login/);
    });
});
