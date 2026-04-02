import { Page, Locator, expect } from '@playwright/test';

export class ProjectPage {
    readonly page: Page;
    readonly createProjectButton: Locator;
    readonly projectNameInput: Locator;
    readonly projectCodeInput: Locator;
    readonly clientSelect: Locator;
    readonly addressInput: Locator;
    readonly submitButton: Locator;
    readonly projectGrid: Locator;
    readonly searchInput: Locator;

    constructor(page: Page) {
        this.page = page;
        this.createProjectButton = page.getByRole('button', { name: /Create New Project/i });
        this.projectNameInput = page.getByPlaceholder(/Enter project name/i);
        this.projectCodeInput = page.getByPlaceholder(/P-001/i);
        this.clientSelect = page.locator('select').first();
        this.addressInput = page.getByPlaceholder(/Site location address/i);
        this.submitButton = page.getByRole('button', { name: /Create Project|Update Project/i });
        this.projectGrid = page.locator('.ag-root-wrapper').first();
        this.searchInput = page.getByPlaceholder(/Search project registry/i);
    }

    async goto() {
        await this.page.goto('/admin/settings/projects');
        // Ag-grid can take time to initialize, wait for the wrapper
        await expect(this.projectGrid).toBeVisible({ timeout: 20000 });
    }

    async createProject(name: string, code: string, address: string) {
        await this.createProjectButton.click();
        await expect(this.projectNameInput).toBeVisible({ timeout: 10000 });

        await this.projectNameInput.fill(name);
        await this.projectCodeInput.fill(code);

        // Wait for clients to load in select
        await this.page.waitForFunction(() => {
            const select = document.querySelector('select');
            return select && select.options.length > 1;
        });
        await this.clientSelect.selectOption({ index: 1 });

        await this.addressInput.fill(address);

        // Submit
        await this.submitButton.click();

        // Wait for modal to close
        await expect(this.projectNameInput).not.toBeVisible({ timeout: 15000 });
    }

    async searchAndVerify(projectName: string) {
        await this.searchInput.clear();
        await this.searchInput.fill(projectName);
        // Wait for grid to filter and show the specific project cell
        const cell = this.page.locator('.ag-cell', { hasText: projectName }).first();
        await expect(cell).toBeVisible({ timeout: 15000 });
    }

    async navigateToProjectDetails(projectName: string) {
        const targetRow = this.page.locator('.ag-center-cols-container .ag-row').filter({ hasText: projectName }).first();
        await targetRow.locator('a[title="Enterprise View"], button[title="Enterprise View"]').first().click({ force: true });
    }
}
