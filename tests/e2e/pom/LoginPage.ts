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

        // Click login button and wait for response
        await this.loginButton.click();

        // Wait for either dashboard URL or error visibility with extended timeout
        const maxRetries = 3;
        let lastError: Error | null = null;

        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                await this.page.waitForURL(/.*dashboard/, { timeout: 30000 });
                return; // Success
            } catch (e) {
                lastError = e as Error;
                console.log(`Login attempt ${attempt} failed: ${e instanceof Error ? e.message : String(e)}`);

                // Check if error message is visible (actual auth error, not network)
                const isErrorVisible = await this.errorMessage.isVisible().catch(() => false);
                if (isErrorVisible) {
                    const text = await this.errorMessage.textContent();
                    throw new Error(`Login failed with error: ${text}`);
                }

                // If it's the last attempt, throw the error
                if (attempt === maxRetries) {
                    throw lastError;
                }

                // Wait before retrying
                console.log(`Retrying login (attempt ${attempt + 1}/${maxRetries})...`);
                await this.page.waitForTimeout(2000);

                // Reset form and try again
                await this.emailInput.fill(email);
                await this.passwordInput.fill(password);
                await this.loginButton.click();
            }
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
