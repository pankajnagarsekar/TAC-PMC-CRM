import { Page, Locator, expect } from '@playwright/test';

export class WorkOrderPage {
    readonly page: Page;
    readonly newWorkOrderButton: Locator;
    readonly categorySelect: Locator;
    readonly vendorSelect: Locator;
    readonly descriptionInput: Locator;
    readonly saveButton: Locator;
    readonly grid: Locator;
    readonly searchInput: Locator;
    readonly addRowButton: Locator;

    constructor(page: Page) {
        this.page = page;
        this.newWorkOrderButton = page.getByRole('button', { name: /New Work Order/i });
        this.categorySelect = page.locator('select').first();
        this.vendorSelect = page.locator('select').nth(1);
        this.descriptionInput = page.getByPlaceholder(/e\.g\., Supply of Ready Mix Concrete/i);
        this.saveButton = page.getByRole('button', { name: /Save & Lock Commitment/i });
        this.grid = page.locator('.ag-root-wrapper').first();
        this.searchInput = page.getByPlaceholder(/Search references\.\.\./i);
        this.addRowButton = page.getByRole('button', { name: /Add Row/i });
    }

    async goto() {
        await this.page.goto('/admin/work-orders');
        // Wait for page to load
        await expect(this.page.getByRole('heading', { name: /Work Orders/i })).toBeVisible();
    }

    async createWorkOrder(description: string, itemDescription: string, qty: string, rate: string) {
        await this.newWorkOrderButton.click();
        await expect(this.page.getByRole('heading', { name: /Create Work Order/i })).toBeVisible();

        // Wait for options to load
        await this.page.waitForFunction(() => {
            const selects = document.querySelectorAll('select');
            return selects.length >= 2 && selects[0].options.length > 1 && selects[1].options.length > 1;
        });

        await this.categorySelect.selectOption({ index: 1 });
        await this.vendorSelect.selectOption({ index: 1 });
        await this.descriptionInput.fill(description);

        // Fill line item in ag-grid
        // Click on the first cell in description column
        await this.page.locator('.ag-cell[col-id="description"]').first().click();
        await this.page.keyboard.type(itemDescription);
        await this.page.keyboard.press('Tab');

        await this.page.keyboard.type(qty);
        await this.page.keyboard.press('Tab');

        await this.page.keyboard.type(rate);
        await this.page.keyboard.press('Enter');

        // Wait a bit for calculations
        await this.page.waitForTimeout(500);

        await this.saveButton.click();

        // Check for over-budget warning dialog and click "Save Anyway" if it appears
        const saveAnywayButton = this.page.getByRole('button', { name: /Save Anyway/i });
        if (await saveAnywayButton.isVisible({ timeout: 5000 }).catch(() => false)) {
            await saveAnywayButton.click();
        }

        // Wait for navigation back or to details
        await expect(this.page).toHaveURL(/\/admin\/work-orders(\/.*)?/);
    }

    async searchAndVerify(woRef: string) {
        await this.searchInput.clear();
        await this.searchInput.fill(woRef);
        // Wait for grid to filter and show the reference
        const cell = this.page.locator('.ag-cell', { hasText: woRef }).first();
        await expect(cell).toBeVisible({ timeout: 15000 });
    }
}
