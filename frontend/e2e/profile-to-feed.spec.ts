import { expect, test } from "@playwright/test";

/**
 * The path a real user takes: sign up, describe the business, see the matches.
 *
 * This is the journey that has to work. Unit tests can all pass while the three
 * pieces fail to talk to each other, which is precisely what this catches.
 */

function uniqueEmail(): string {
  return `e2e-${Date.now()}-${Math.floor(Math.random() * 10000)}@example.com`;
}

const PASSWORD = "correct-horse-battery-staple";

test.describe("profile to ranked feed", () => {
  test("a DPIIT-recognised startup sees ranked matches with reasons", async ({ page }) => {
    await page.goto("/");

    // --- Sign up ---
    await expect(page.getByRole("heading", { name: /Create your account/i })).toBeVisible();
    await page.getByLabel("Email", { exact: true }).fill(uniqueEmail());
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();

    // --- Profile ---
    await expect(page.getByRole("heading", { name: /Tell us about your business/i })).toBeVisible();
    await page.getByLabel("Business name").fill("Priya EdTech Private Limited");
    await page.getByLabel("State", { exact: true }).selectOption("Maharashtra");
    await page.getByLabel("Sector", { exact: true }).selectOption("edtech");
    await page.getByLabel("Stage", { exact: true }).selectOption("early");
    await page.getByLabel("Employees").fill("8");
    await page.getByLabel("Incorporation date").fill("2025-03-01");
    await page.getByLabel("DPIIT startup recognition").check();
    await page.getByLabel("GST registration").check();
    await page.getByLabel("Annual turnover in rupees").fill("1200000");
    await page.getByRole("button", { name: /See what I qualify for/i }).click();

    // --- Ranked feed ---
    await expect(page.getByRole("heading", { name: "Your matches" })).toBeVisible();
    await expect(page.getByText(/Checked your profile against 40 active schemes/)).toBeVisible();

    // SISFS requires DPIIT recognition and an entity under two years old, both of
    // which this profile satisfies, so it must appear.
    await expect(page.getByRole("link", { name: /Startup India Seed Fund/i })).toBeVisible();

    // Confidence is always expressed as a checked fraction, never as a bare
    // probability of approval.
    await expect(page.getByText(/of \d+ requirements/).first()).toBeVisible();

    // The advisory caveat must be on the page, not only in the terms.
    await expect(page.getByText(/not a determination of eligibility/i)).toBeVisible();
  });

  test("schemes the applicant does not qualify for stay visible with a reason", async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByLabel("Email", { exact: true }).fill(uniqueEmail());
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();

    // No Udyam registration, which gates several MSME schemes.
    await page.getByLabel("Business name").fill("No Udyam Enterprises");
    await page.getByLabel("State", { exact: true }).selectOption("Punjab");
    await page.getByLabel("Sector", { exact: true }).selectOption("manufacturing");
    await page.getByLabel("Stage", { exact: true }).selectOption("growth");
    await page.getByRole("button", { name: /See what I qualify for/i }).click();

    await expect(page.getByRole("heading", { name: "Your matches" })).toBeVisible();

    const toggle = page.getByRole("button", { name: /schemes you do not currently qualify/i });
    await expect(toggle).toBeVisible();
    await toggle.click();

    // CGTMSE requires Udyam registration, so it must be listed as ruled out
    // rather than silently omitted. Matched by full name, since the corpus
    // also contains the Credit Guarantee Scheme for Startups (CGSS), a
    // different, real scheme that would otherwise also match a loose
    // "Credit Guarantee Scheme" substring.
    await expect(
      page.getByRole("link", { name: /Credit Guarantee Scheme for Micro and Small Enterprises/i })
    ).toBeVisible();
    await expect(page.getByText(/requirement not met/i).first()).toBeVisible();
  });

  test("an incomplete profile is told what to add rather than shown a failure", async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByLabel("Email", { exact: true }).fill(uniqueEmail());
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();

    // Turnover and incorporation date deliberately omitted.
    await page.getByLabel("Business name").fill("Sparse Profile Co");
    await page.getByLabel("State", { exact: true }).selectOption("Kerala");
    await page.getByLabel("Sector", { exact: true }).selectOption("software");
    await page.getByLabel("Stage", { exact: true }).selectOption("early");
    await page.getByRole("button", { name: /See what I qualify for/i }).click();

    await expect(page.getByRole("heading", { name: "Your matches" })).toBeVisible();
    // The product asks for the missing data instead of reporting ineligibility.
    await expect(page.getByText(/to settle the most open requirements/i)).toBeVisible();
  });
});


test.describe("one-click judge demo", () => {
  test("provisions Arjun and reaches an application-ready SISFS draft", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("button", { name: /Launch live judge demo/i }).click();

    await expect(page.getByRole("heading", { name: "ZEN Club", level: 1 })).toBeVisible();
    await expect(page.getByText("40", { exact: true }).first()).toBeVisible();

    await page.getByRole("link", { name: /Startup India Seed Fund Scheme/i }).click();
    await expect(page.getByRole("heading", { name: /Startup India Seed Fund Scheme/i })).toBeVisible();
    await expect(page.getByText(/3 have · 1 missing/i)).toBeVisible();

    await page.getByRole("button", { name: /Generate draft/i }).click();
    await expect(page.getByText(/Application workspace generated/i)).toBeVisible();
    await expect(page.getByText(/fields prepared/i)).toBeVisible();
    await expect(page.getByText(/This is a draft, not a submission/i)).toBeVisible();
  });
});
