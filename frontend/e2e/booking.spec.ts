import { expect, test, type Browser, type Page } from "@playwright/test";

const MOBILE = { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true };
const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

async function registerOwner(page: Page, slug: string) {
  await page.goto("/register");
  await page.getByLabel("Business name").fill(`E2E Salon ${slug}`);
  await page.getByLabel("Booking link").fill(slug);
  await page.getByLabel("Email").fill(`${slug}@e2e.test`);
  await page.getByLabel("Password").fill("Passw0rd!");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard\/services$/);

  await page.getByRole("button", { name: "+ Add service" }).click();
  await page.getByLabel("Name").fill("Haircut");
  await page.getByLabel("Duration (min)").fill("30");
  await page.getByLabel("Price (₹)").fill("300");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("30 min · ₹300")).toBeVisible();

  await page.getByRole("link", { name: "Hours" }).first().click();
  for (const day of WEEKDAYS) await page.getByLabel(`${day} closed`).uncheck(); // defaults to 10:00–18:00
  await page.getByRole("button", { name: "Save hours" }).click();
  await expect(page.getByText("Working hours saved")).toBeVisible();
}

async function openTomorrowFirstSlot(browser: Browser, slug: string) {
  const ctx = await browser.newContext(MOBILE);
  const page = await ctx.newPage();
  await page.goto(`/${slug}`);
  await page.getByRole("radio", { name: /Haircut/ }).click();
  await page.getByRole("radiogroup", { name: "Dates" }).getByRole("radio").nth(1).click(); // tomorrow
  const slot = page.getByRole("radiogroup", { name: "Times" }).getByRole("radio").first();
  await slot.click();
  return { ctx, page, slotLabel: (await slot.textContent()) ?? "" };
}

test("owner sets up, customer books on mobile, owner completes it", async ({ page, browser }) => {
  const slug = `e2e-${Date.now().toString(36)}`;
  await registerOwner(page, slug);

  const { ctx, page: mobile, slotLabel } = await openTomorrowFirstSlot(browser, slug);
  // No horizontal page scroll at phone width
  const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
  await mobile.getByLabel("Name").fill("Asha Verma");
  await mobile.getByLabel("Mobile number").fill("9123456780");
  await mobile.getByRole("button", { name: "Confirm booking" }).click();
  await expect(mobile.getByText("You're booked!")).toBeVisible();
  const ref = (await mobile.locator("dd.font-mono").textContent()) ?? "";
  expect(ref).toMatch(/^APT-\d{8}-0001$/);
  await ctx.close();

  await page.getByRole("link", { name: "Today" }).first().click();
  await page.getByRole("button", { name: "Next day" }).click();
  const row = page.getByTestId(`appt-${ref}`);
  await expect(row).toContainText("Asha Verma");
  await expect(row).toContainText(slotLabel);
  await row.getByRole("button", { name: "Complete" }).click();
  await expect(row.getByText("Completed")).toBeVisible();
  await expect(page.getByTestId("day-summary")).toContainText("1 booking · 0 no-shows · Est. ₹300");
});

test("two phones confirm the same slot: one succeeds, one gets the 409 toast", async ({ page, browser }) => {
  const slug = `e2e-race-${Date.now().toString(36)}`;
  await registerOwner(page, slug);

  const a = await openTomorrowFirstSlot(browser, slug);
  const b = await openTomorrowFirstSlot(browser, slug);
  expect(a.slotLabel).toBe(b.slotLabel);
  for (const [p, phone] of [
    [a.page, "9000000001"],
    [b.page, "9000000002"],
  ] as const) {
    await p.getByLabel("Name").fill("Racer");
    await p.getByLabel("Mobile number").fill(phone);
  }
  await Promise.all([
    a.page.getByRole("button", { name: "Confirm booking" }).click(),
    b.page.getByRole("button", { name: "Confirm booking" }).click(),
  ]);

  const outcome = async (p: Page) => {
    const booked = p.getByText("You're booked!");
    const toast = p.getByText("This slot was just booked. Please pick another time.");
    await expect(booked.or(toast)).toBeVisible();
    return (await booked.isVisible()) ? "booked" : "conflict";
  };
  const results = [await outcome(a.page), await outcome(b.page)].sort();
  expect(results).toEqual(["booked", "conflict"]);
  await a.ctx.close();
  await b.ctx.close();
});
