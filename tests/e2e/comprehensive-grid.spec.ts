import { test, expect } from '@playwright/test';
import { LoginPage } from './pom/LoginPage';
import { ProjectPage } from './pom/ProjectPage';
import { DashboardPage } from './pom/DashboardPage';

test.describe('Project Planner Grid - Comprehensive Validation', () => {
    let loginPage: LoginPage;
    let projectPage: ProjectPage;
    let dashboardPage: DashboardPage;
    let projectName: string;

    test.beforeEach(async ({ page }) => {
        // High timeout for setup
        test.setTimeout(120000);
        loginPage = new LoginPage(page);
        projectPage = new ProjectPage(page);
        dashboardPage = new DashboardPage(page);
        projectName = `SCHEDULER-V-CORE-${Date.now()}`;

        await loginPage.goto();
        await loginPage.login('amit@thirdangleconcept.com', 'Admin@1234');
        await expect(page).toHaveURL(/.*dashboard/, { timeout: 30000 });
    });

    test('Full Lifecycle: Grid, Drawer, 5-Level Hierarchy, and CPM', async ({ page }) => {
        // High timeout for complex multi-step scenario
        test.setTimeout(600000);

        // ──────────────────────────────────────────────────────────────────────────
        // 1. PROJECT SETUP
        // ──────────────────────────────────────────────────────────────────────────
        await projectPage.goto();
        await projectPage.createProject(projectName, 'VAL-99', 'Validation Sector 7');
        await dashboardPage.goto();
        await dashboardPage.selectProject(projectName);

        // ──────────────────────────────────────────────────────────────────────────
        // 2. GRID VISIBILITY & COLUMNS
        // ──────────────────────────────────────────────────────────────────────────
        await page.goto('/admin/scheduler');
        await expect(page.getByText('Project Planner').first()).toBeVisible();

        const expectedHeaders = [
            "WBS Code", "Task Description", "Mode", "Start Date",
            "Finish Date", "Duration", "% Comp", "Status", "Heads", "Constraint", "Menu"
        ];
        for (const header of expectedHeaders) {
            await expect(page.getByText(header).first()).toBeVisible();
        }

        // ──────────────────────────────────────────────────────────────────────────
        // 3. CRUD & BASIC EDITING
        // ──────────────────────────────────────────────────────────────────────────
        // Add Task A
        await page.getByRole('button', { name: /Add Task/i }).first().click();
        await expect(page.getByText(/Synced/i)).toBeVisible();

        // Edit Task A name in grid
        const taskRow1 = page.locator('.grid.items-stretch').nth(1);
        const nameInput = taskRow1.locator('input[type="text"]').first();
        await nameInput.fill('Phase Alpha - Initial');
        await nameInput.press('Tab');
        await expect(page.getByText(/Synced/i)).toBeVisible();

        // Open Task Drawer via Pencil
        await taskRow1.locator('button[title="Edit task"]').click();
        const drawer = page.locator('aside');
        await expect(drawer).toBeVisible();

        // Update Duration and % Comp in Drawer
        await page.getByRole('tab', { name: "Task Brief" }).click();
        const durationField = page.locator('label:has-text("Duration")').locator('input');
        await durationField.fill('15');
        await durationField.press('Tab');

        const compField = page.locator('label:has-text("% Complete")').locator('input');
        await compField.fill('25');
        await compField.press('Tab');
        await expect(page.getByText(/Synced/i)).toBeVisible();

        // ──────────────────────────────────────────────────────────────────────────
        // 4. TASK DRAWER TABS VERIFICATION
        // ──────────────────────────────────────────────────────────────────────────
        const drawerTabs = [
            { name: "Task Brief", check: "Task name" },
            { name: "Project Network", check: "Confirm Network Link" },
            { name: "Economics", check: "Contract Value" },
            { name: "Field Notes", check: "Raw Meeting Notes" },
            { name: "Log Registry", check: "Task History" }
        ];

        for (const tab of drawerTabs) {
            const trigger = page.getByRole('tab', { name: tab.name });
            await trigger.click();
            await expect(page.getByText(tab.check).first()).toBeVisible();
        }

        // ──────────────────────────────────────────────────────────────────────────
        // 5. FIVE-LEVEL HIERARCHY NESTING
        // ──────────────────────────────────────────────────────────────────────────
        // Level 1: Phase Alpha (already exists as task-1)
        await page.getByRole('tab', { name: "Task Brief" }).click();
        await page.locator('select').filter({ hasText: /Sub-Task/ }).selectOption('summary');
        await expect(page.getByText(/Synced/i)).toBeVisible();

        // Level 2
        await page.getByRole('button', { name: /Add Task/i }).first().click();
        await expect(page.getByText(/Synced/i)).toBeVisible();
        const taskRow2 = page.locator('.grid.items-stretch').nth(2);
        await taskRow2.locator('button[title="Edit task"]').click();
        await page.locator('input[placeholder="example: task-42"]').fill('task-1');
        await page.locator('input[placeholder="example: task-42"]').press('Tab');
        await page.locator('select').filter({ hasText: /Sub-Task/ }).selectOption('summary');
        await page.locator('input').first().fill('L2 - Sub Group');
        await page.locator('input').first().press('Enter');
        await expect(page.getByText(/Synced/i)).toBeVisible();

        // Level 3-5
        for (let i = 3; i <= 5; i++) {
            await page.getByRole('button', { name: /Add Task/i }).first().click();
            await expect(page.getByText(/Synced/i)).toBeVisible();
            const currentRow = page.locator('.grid.items-stretch').nth(i);
            await currentRow.locator('button[title="Edit task"]').click();
            await page.locator('input[placeholder="example: task-42"]').fill(`task-${i - 1}`);
            await page.locator('input[placeholder="example: task-42"]').press('Tab');
            await page.locator('input').first().fill(`Level ${i} Task`);
            await page.locator('input').first().press('Enter');
            await expect(page.getByText(/Synced/i)).toBeVisible();
        }

        // Verify WBS structure in Grid
        await expect(page.getByText('1.1.1.1.1')).toBeVisible();

        // ──────────────────────────────────────────────────────────────────────────
        // 6. TIMELINE PROPAGATION (CPM)
        // ──────────────────────────────────────────────────────────────────────────
        await page.getByRole('button', { name: /Add Task/i }).first().click();
        const row6 = page.locator('.grid.items-stretch').nth(6);
        await row6.locator('button[title="Edit task"]').click();
        await page.getByRole('tab', { name: "Project Network" }).click();
        await page.getByPlaceholder(/example: task-42/i).fill('task-5');
        await page.getByRole('button', { name: /Confirm Network Link/i }).click();
        await expect(page.getByText(/Synced/i)).toBeVisible();

        const finishDate6 = await page.locator('.grid.items-stretch').nth(6).locator('input[type="date"]').nth(1).inputValue();

        await page.locator('.grid.items-stretch').nth(5).locator('button[title="Edit task"]').click();
        await page.getByRole('tab', { name: "Task Brief" }).click();
        await page.locator('label:has-text("Duration")').locator('input').fill('20');
        await page.locator('label:has-text("Duration")').locator('input').press('Tab');
        await expect(page.getByText(/Synced/i)).toBeVisible();

        const newFinishDate6 = await page.locator('.grid.items-stretch').nth(6).locator('input[type="date"]').nth(1).inputValue();
        expect(newFinishDate6).not.toBe(finishDate6);

        // ──────────────────────────────────────────────────────────────────────────
        // 7. DELETION
        // ──────────────────────────────────────────────────────────────────────────
        await page.locator('.grid.items-stretch').nth(6).locator('button[title="Remove task locally"]').click();
        await expect(page.getByText(/Task removed locally/i)).toBeVisible();
    });
});
