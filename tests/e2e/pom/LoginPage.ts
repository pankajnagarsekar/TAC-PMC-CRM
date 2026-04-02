import { Page, Locator, expect } from '@playwright/test';

export class LoginPage {
    readonly page: Page;
    readonly emailInput: Locator;
    readonly passwordInput: Locator;
    readonly loginButton: Locator;
    readonly errorMessage: Locator;
    readonly sidebar: Locator;
    readonly logoutButton: Locator;

    constructor(page: Page) {
        this.page = page;
        this.emailInput = page.locator('#email');
        this.passwordInput = page.locator('#password');
        this.loginButton = page.locator('#login-btn');
        this.errorMessage = page.locator('.text-red-400, .text-red-500').first();
        this.sidebar = page.locator('aside');
        this.logoutButton = page.getByRole('button', { name: /Sign Out/i });
    }

    async goto() {
        await this.page.goto('/login');
    }

    async login(email: string, password: string) {
        await this.emailInput.fill(email);
        await this.passwordInput.fill(password);

        // Use Promise.race to either wait for navigation or an error message
        await this.loginButton.click();

        // Wait for either dashboard URL or error visibility
        try {
            await this.page.waitForURL(/.*dashboard/, { timeout: 8000 });
        } catch (e) {
            // Check if error message is visible
            const isErrorVisible = await this.errorMessage.isVisible();
            if (isErrorVisible) {
                const text = await this.errorMessage.textContent();
                throw new Error(`Login failed with error: ${text}`);
            }
            throw e;
        }
    }

    async logout() {
        // Force logout since sidebar might be collapsed
        await this.logoutButton.click({ force: true });
        await expect(this.page).toHaveURL(/.*login/);
    }

    async expectDashboard() {
        await expect(this.page).toHaveURL(/.*dashboard/, { timeout: 15000 });
        await expect(this.sidebar).toBeVisible({ timeout: 15000 });
    }

    async expectError(message?: string) {
        // Increased timeout for animations
        await expect(this.errorMessage).toBeVisible({ timeout: 10000 });
        if (message) {
            await expect(this.errorMessage).toContainText(message);
        }
    }
}
