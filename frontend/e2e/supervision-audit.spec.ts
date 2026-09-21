import { test, expect } from "@playwright/test";
import { TEST_USERS } from "./fixtures/test-data";

test.describe("E2E Supervision Dashboard & Audit Viewer", () => {
  test.beforeEach(async ({ page }) => {
    // Authenticate as SUPERADMIN
    await page.goto("/login");
    await page.fill('input[type="email"], input[name="email"]', TEST_USERS.superadmin.email);
    await page.fill('input[type="password"], input[name="password"]', TEST_USERS.superadmin.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(admin)?$/);
  });

  test("supervision tab displays KPI metrics and processes table", async ({ page }) => {
    await page.goto("/admin");

    // Click Supervision tab if not active
    const supervisionBtn = page.getByRole("button", { name: /supervisión institucional/i });
    if (await supervisionBtn.isVisible()) {
      await supervisionBtn.click();
    }

    // Verify macro KPI cards are present
    await expect(page.getByText(/procesos curriculares/i)).toBeVisible();
    await expect(page.getByText(/programas formación/i)).toBeVisible();
    await expect(page.getByText(/proyectos formativos/i)).toBeVisible();
    await expect(page.getByText(/planeaciones pedagógicas/i)).toBeVisible();
  });

  test("audit viewer displays sanitized logs and opens detail payload modal", async ({ page }) => {
    await page.goto("/admin");

    // Click Audit tab
    const auditBtn = page.getByRole("button", { name: /visor de auditoría/i });
    await auditBtn.click();

    // Verify audit banner and table
    await expect(page.getByText(/visor de auditoría inmutable/i)).toBeVisible();

    // If an event row exists, click "Carga Útil"
    const payloadBtn = page.getByRole("button", { name: /carga útil/i }).first();
    if (await payloadBtn.isVisible()) {
      await payloadBtn.click();
      await expect(page.getByText(/registro de auditoría institucional/i)).toBeVisible();
      // Ensure raw passwords are NOT visible
      await expect(page.locator("text=[REDACTED]")).toBeVisible();
    }
  });

  test("leaders are barred from accessing /admin", async ({ page }) => {
    // Log out and log in as leader
    await page.goto("/login");
    await page.fill('input[type="email"], input[name="email"]', TEST_USERS.lider.email);
    await page.fill('input[type="password"], input[name="password"]', TEST_USERS.lider.password);
    await page.click('button[type="submit"]');

    // Try navigating to /admin
    await page.goto("/admin");

    // Should be redirected or receive access denied
    await expect(page).not.toHaveURL(/\/admin$/);
  });
});
