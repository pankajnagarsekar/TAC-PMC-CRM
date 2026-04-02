import { Page, Locator, expect } from '@playwright/test';

export class DashboardPage {
    readonly page: Page;
    readonly searchInput: Locator;
    readonly switchProjectButton: Locator;
    readonly activeContextBar: Locator;

    constructor(page: Page) {
        this.page = page;
        this.searchInput = page.getByPlaceholder(/Search projects by name or code/i);
        this.switchProjectButton = page.getByRole('button', { name: /Switch Project/i });
        this.activeContextBar = page.locator('div').filter({ hasText: /^Active Context$/i }).first();
    }

    async goto() {
        await this.page.goto('/admin/dashboard');
    }

    async selectProject(name: string) {
        // If we are currently in an active project context, click "Switch Project" to see the list again
        if (await this.switchProjectButton.isVisible()) {
            await this.switchProjectButton.click();
        }

        await expect(this.searchInput).toBeVisible();
        await this.searchInput.fill(name);

        // Select the project from the dashboard list (buttons with h4 title)
        // Avoid the search text itself
        await this.page.locator(`h4:has-text("${name}")`).first().click();
    }

    async expectActiveProject(name: string) {
        // Check for the name in the context bar specifically
        const activeProjectName = this.page.locator('p.text-xl', { hasText: name });
        await expect(activeProjectName).toBeVisible();
    }
}
