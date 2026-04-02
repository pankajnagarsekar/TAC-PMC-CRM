import { Page, Locator, expect } from '@playwright/test';

export class SiteOperationsPage {
    readonly page: Page;
    readonly dprTabButton: Locator;
    readonly attendanceTabButton: Locator;
    readonly voiceLogsTabButton: Locator;
    readonly fundsTabButton: Locator;
    readonly searchInput: Locator;
    readonly statusFilter: Locator;
    readonly siteOperationsGrid: Locator;

    constructor(page: Page) {
        this.page = page;
        this.dprTabButton = page.getByRole('button', { name: /DPR Review/i });
        this.attendanceTabButton = page.getByRole('button', { name: /Worker Attendance/i });
        this.voiceLogsTabButton = page.getByRole('button', { name: /Voice Logs/i });
        this.fundsTabButton = page.getByRole('button', { name: /Site Funds/i });
        this.searchInput = page.getByPlaceholder(/Search notes.../i);
        this.statusFilter = page.locator('select').first();
        this.siteOperationsGrid = page.locator('.ag-root-wrapper').first();
    }

    async goto() {
        await this.page.goto('/admin/site-operations');
        await expect(this.page.getByRole('heading', { name: /Site Operations/i })).toBeVisible();
    }

    async switchTab(tab: 'dprs' | 'attendance' | 'voice-logs' | 'funds') {
        const tabButtons = {
            'dprs': this.dprTabButton,
            'attendance': this.attendanceTabButton,
            'voice-logs': this.voiceLogsTabButton,
            'funds': this.fundsTabButton
        };
        await tabButtons[tab].click();
        // Wait for specific grid content or loading to finish
        await this.page.waitForTimeout(1000);
    }

    async verifyDPRVisible(notesKeyword: string) {
        await this.searchInput.clear();
        await this.searchInput.fill(notesKeyword);
        const cell = this.page.locator('.ag-cell', { hasText: notesKeyword }).first();
        await expect(cell).toBeVisible({ timeout: 15000 });
    }

    async verifyAttendanceVisible(workerName: string) {
        // Attendance tab might not have a search but we can filter by date or just look in the grid
        const cell = this.page.locator('.ag-cell', { hasText: workerName }).first();
        await expect(cell).toBeVisible({ timeout: 15000 });
    }
}
