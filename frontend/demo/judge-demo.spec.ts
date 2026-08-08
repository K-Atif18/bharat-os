import { expect, type Locator, type Page, test } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const MODES = ["discover", "rehearse", "record"] as const;
type DemoMode = (typeof MODES)[number];

const requestedMode = process.env.BHARAT_OS_DEMO_MODE ?? "record";
if (!MODES.includes(requestedMode as DemoMode)) {
  throw new Error(`BHARAT_OS_DEMO_MODE must be one of: ${MODES.join(", ")}`);
}
const mode = requestedMode as DemoMode;

const viewport = { width: 1280, height: 720 };
const assetRoot = path.resolve(__dirname, "../../docs/assets");
const screenshotDir = path.join(assetRoot, "screenshots");
const videoDir = path.join(assetRoot, "demo");
const rawVideoDir = path.resolve(process.cwd(), "test-results/demo/videos");
const finalVideo = path.join(videoDir, "bharat-os-judge-demo.webm");

async function dumpInteractiveElements(page: Page, label: string): Promise<void> {
  const elements = await page.evaluate(() =>
    Array.from(
      document.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement | HTMLButtonElement>(
        "input, select, textarea, button",
      ),
    )
      .filter((element) => element.offsetParent !== null)
      .map((element) => ({
        tag: element.tagName.toLowerCase(),
        type: "type" in element ? element.type : "",
        name: element.getAttribute("name") ?? "",
        label: element.getAttribute("aria-label") ?? "",
        text: element.textContent?.trim().slice(0, 80) ?? "",
        options:
          element instanceof HTMLSelectElement
            ? Array.from(element.options).map((option) => ({ value: option.value, text: option.text }))
            : undefined,
      })),
  );
  console.log(`\nDISCOVERY ${label} (${page.url()})\n${JSON.stringify(elements, null, 2)}`);
}

async function injectDemoChrome(page: Page): Promise<void> {
  if (mode !== "record") return;
  await page.evaluate(() => {
    if (!document.getElementById("demo-cursor")) {
      const cursor = document.createElement("div");
      cursor.id = "demo-cursor";
      cursor.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M5 3L19 12L12 13L9 20L5 3Z" fill="white" stroke="black" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
      cursor.style.cssText = "position:fixed;left:24px;top:24px;z-index:999999;pointer-events:none;width:24px;height:24px;transition:left .1s,top .1s;filter:drop-shadow(1px 1px 2px rgba(0,0,0,.3))";
      document.body.appendChild(cursor);
      document.addEventListener("mousemove", (event) => {
        cursor.style.left = `${event.clientX}px`;
        cursor.style.top = `${event.clientY}px`;
      });
    }
    if (!document.getElementById("demo-subtitle")) {
      const subtitle = document.createElement("div");
      subtitle.id = "demo-subtitle";
      subtitle.style.cssText = "position:fixed;bottom:0;left:0;right:0;z-index:999998;pointer-events:none;padding:12px 24px;text-align:center;background:rgba(0,0,0,.78);color:white;font:500 16px -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;letter-spacing:.2px;opacity:0;transition:opacity .25s";
      document.body.appendChild(subtitle);
    }
  });
}

async function showSubtitle(page: Page, text: string): Promise<void> {
  if (mode !== "record") return;
  await injectDemoChrome(page);
  await page.evaluate((nextText) => {
    const subtitle = document.getElementById("demo-subtitle");
    if (!subtitle) return;
    subtitle.textContent = nextText;
    subtitle.style.opacity = nextText ? "1" : "0";
  }, text);
  if (text) await page.waitForTimeout(650);
}

async function pause(page: Page, milliseconds: number): Promise<void> {
  if (mode === "record") await page.waitForTimeout(milliseconds);
}

async function moveAndClick(page: Page, locator: Locator, label: string): Promise<void> {
  await expect(locator, `${label} should be visible`).toBeVisible();
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  if (!box) throw new Error(`Could not determine the position of ${label}`);
  if (mode === "record") {
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 12 });
    await page.waitForTimeout(350);
  }
  await locator.click();
  await pause(page, 900);
}

async function panElements(page: Page, locator: Locator, maximum = 4): Promise<void> {
  if (mode !== "record") return;
  const elements = await locator.all();
  for (const element of elements.slice(0, maximum)) {
    const box = await element.boundingBox();
    if (box && box.y > 0 && box.y < viewport.height - 40) {
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 10 });
      await page.waitForTimeout(450);
    }
  }
}

async function capture(page: Page, filename: string, fullPage = false): Promise<void> {
  if (mode !== "record") return;
  await page.screenshot({
    path: path.join(screenshotDir, filename),
    fullPage,
    animations: "disabled",
    style: "#demo-cursor, #demo-subtitle { display: none !important; }",
  });
}

test.describe("Bharat OS judge demo media", () => {
  test.setTimeout(180_000);

  test("discovers, rehearses, or records the real application journey", async ({ browser }) => {
    await mkdir(screenshotDir, { recursive: true });
    await mkdir(videoDir, { recursive: true });
    await mkdir(rawVideoDir, { recursive: true });

    const context = await browser.newContext({
      viewport,
      ...(mode === "record" ? { recordVideo: { dir: rawVideoDir, size: viewport } } : {}),
    });
    const page = await context.newPage();
    let completed = false;

    try {
      await page.goto("/");
      const launchDemo = page.getByRole("button", { name: /Launch live judge demo/i });
      await expect(launchDemo).toBeVisible();
      if (mode === "discover") await dumpInteractiveElements(page, "landing");
      await capture(page, "01-landing.png");
      await injectDemoChrome(page);
      await showSubtitle(page, "Meet Arjun — a DPIIT-recognised startup founder");
      await pause(page, 1_400);

      await showSubtitle(page, "One click builds a real, isolated workspace");
      await moveAndClick(page, launchDemo, "Launch live judge demo");
      await page.waitForURL("**/dashboard");
      await expect(page.getByText("ZEN Club")).toBeVisible();
      await expect(page.getByText("15", { exact: true }).first()).toBeVisible();
      if (mode === "discover") await dumpInteractiveElements(page, "dashboard");
      await capture(page, "02-dashboard.png");
      await injectDemoChrome(page);
      await showSubtitle(page, "20 schemes ranked against the same profile");
      await panElements(page, page.locator("section").first().locator("dd"), 3);
      await pause(page, 1_200);

      const sisfs = page.getByRole("link", { name: /Startup India Seed Fund Scheme/i }).first();
      await showSubtitle(page, "Open a sourced, criterion-by-criterion assessment");
      await moveAndClick(page, sisfs, "Startup India Seed Fund Scheme");
      await page.waitForURL("**/schemes/sisfs");
      await expect(page.getByRole("heading", { name: /Startup India Seed Fund Scheme/i })).toBeVisible();
      const documentSummary = page.getByText(/3 have · 1 missing/i);
      await expect(documentSummary).toBeVisible();
      if (mode === "discover") await dumpInteractiveElements(page, "scheme deep dive");
      await documentSummary.scrollIntoViewIfNeeded();
      await pause(page, 900);
      await capture(page, "03-sisfs-deep-dive.png");
      await injectDemoChrome(page);
      await showSubtitle(page, "The vault shows 3 documents ready and 1 missing");
      await pause(page, 1_500);

      const generateDraft = page.getByRole("button", { name: "Generate draft" });
      await showSubtitle(page, "Generate an editable application workspace");
      await moveAndClick(page, generateDraft, "Generate draft");
      const workspace = page.getByText("Application workspace generated");
      await expect(workspace).toBeVisible();
      await expect(page.getByText(/fields prepared/i)).toBeVisible();
      await expect(page.getByText(/This is a draft, not a submission/i)).toBeVisible();
      await workspace.scrollIntoViewIfNeeded();
      await pause(page, 900);
      await capture(page, "04-application-workspace.png");
      await showSubtitle(page, "Human review stays mandatory — nothing is submitted");
      await pause(page, 1_900);

      const backToMatches = page.getByRole("link", { name: /Back to your matches/i });
      await moveAndClick(page, backToMatches, "Back to matches");
      await page.waitForURL("**/dashboard");
      const privacy = page.getByRole("link", { name: /Privacy & data/i });
      await showSubtitle(page, "Privacy controls are available from the dashboard");
      await moveAndClick(page, privacy, "Privacy and data");
      await page.waitForURL("**/settings");
      await expect(page.getByRole("heading", { name: "Your data and consent" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Purpose-specific consent" })).toBeVisible();
      await expect(page.getByRole("link", { name: /Download .ics calendar/i })).toBeVisible();
      if (mode === "discover") await dumpInteractiveElements(page, "privacy settings");
      await capture(page, "05-privacy-settings.png", true);
      await injectDemoChrome(page);
      await showSubtitle(page, "Consent, calendar export, and erasure stay user-controlled");
      await panElements(page, page.locator("button"), 4);
      await pause(page, 2_100);
      await showSubtitle(page, "Bharat OS — from eligibility reasoning to execution");
      await pause(page, 2_200);
      await showSubtitle(page, "");

      completed = true;
    } finally {
      const video = page.video();
      await context.close();
      if (mode === "record" && completed && video) {
        await video.saveAs(finalVideo);
        console.log(`Demo video saved to ${finalVideo}`);
      }
    }
  });
});
