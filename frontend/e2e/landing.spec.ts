import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  // Public UI checks deliberately use an anonymous session, without a live backend.
  await page.route("**/auth/refresh", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: '{"detail":"No active session"}',
    }),
  );
});

for (const viewport of [
  { width: 1440, height: 900 },
  { width: 1920, height: 1080 },
  { width: 390, height: 844 },
  { width: 820, height: 1180 },
]) {
  test(`landing layout ${viewport.width}x${viewport.height}`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      /Construye planeaciones.*pedagógicas con claridad.*y acompañamiento/,
    );
    await expect(
      page
        .getByRole("region", { name: "Proceso y capacidades de ASGARD" })
        .getByRole("listitem"),
    ).toHaveCount(5);
    const instructor = page.getByRole("img", { name: /Instructora del SENA/ });
    await expect(instructor).toBeVisible();
    await expect
      .poll(() =>
        instructor.evaluate(
          (image: HTMLImageElement) => image.complete && image.naturalWidth > 0,
        ),
      )
      .toBe(true);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    expect(
      await page
        .locator('i[class*="particle"]')
        .first()
        .evaluate((el) => getComputedStyle(el).animationName),
    ).toBe("none");
    await page.screenshot({
      path: `test-results/landing-${viewport.width}.png`,
      fullPage: true,
    });
    await page.getByRole("link", { name: "Ver cómo funciona" }).click();
    await expect(page).toHaveURL(/#proceso$/);
    await expect(
      page.getByRole("region", { name: "Proceso y capacidades de ASGARD" }),
    ).toBeInViewport();
  });
}

test("both public entry buttons reuse the existing login", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Iniciar Sesión en ASGARD" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "✕", exact: true }).click();
  await page.getByRole("button", { name: "Comenzar ahora" }).click();
  await expect(
    page.getByRole("heading", { name: "Iniciar Sesión en ASGARD" }),
  ).toBeVisible();
});

test("the existing master dashboard is available at its new route", async ({
  page,
}) => {
  await page.route("**/dashboard/programas", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: '{"detail":"Not authenticated"}',
    }),
  );
  await page.goto("/dashboard");
  await expect(
    page.getByRole("heading", {
      name: "Panel de gestion de programa, proyecto y planeacion",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Nuevo programa" }),
  ).toHaveAttribute("href", "/programa?nuevo=programa");
});
