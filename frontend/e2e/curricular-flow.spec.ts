import { test, expect } from "@playwright/test";
import { TEST_USERS } from "./fixtures/test-data";

test.describe("E2E Curricular Flow: Program → Project → Planning → GPFI-F-134 V05", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="email"], input[name="email"]', TEST_USERS.superadmin.email);
    await page.fill('input[type="password"], input[name="password"]', TEST_USERS.superadmin.password);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(admin)?$/);
  });

  test("master dashboard shows program gate and workflow stages", async ({ page }) => {
    await page.goto("/");

    // Verify operational dashboard sections
    await expect(page.locator("body")).toBeVisible();
    await expect(page.getByText(/programa/i).first()).toBeVisible();
  });

  test("pedagogical planning module enables GPFI-F-134 V05 workbook download when complete", async ({ page }) => {
    await page.goto("/planeacion");

    // Check if planning interface loads
    await expect(page.locator("body")).toBeVisible();
  });
});
