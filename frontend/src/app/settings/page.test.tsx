import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SettingsPage from "@/app/settings/page";

const mocks = vi.hoisted(() => ({
  eraseAccount: vi.fn(),
  getAccount: vi.fn(),
  router: { replace: vi.fn() },
  updateConsent: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => mocks.router,
  usePathname: () => "/settings",
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    eraseAccount: mocks.eraseAccount,
    getAccount: mocks.getAccount,
    updateConsent: mocks.updateConsent,
  };
});

const ACTIVE_CONSENTS = [
  {
    purpose: "scheme_matching",
    granted_at: "2026-07-31T12:00:00Z",
    withdrawn_at: null,
    policy_version: "2026-07-1",
    is_active: true,
  },
  {
    purpose: "document_storage",
    granted_at: "2026-07-31T12:00:00Z",
    withdrawn_at: null,
    policy_version: "2026-07-1",
    is_active: true,
  },
] as const;

beforeEach(() => {
  vi.clearAllMocks();
  mocks.getAccount.mockResolvedValue({
    id: "00000000-0000-0000-0000-000000000001",
    email: "founder@example.com",
    created_at: "2026-07-31T12:00:00Z",
    consents: ACTIVE_CONSENTS,
    has_profile: true,
  });
});

describe("SettingsPage", () => {
  it("confirms destructive consent withdrawal and reflects the API result", async () => {
    mocks.updateConsent.mockResolvedValue([
      { ...ACTIVE_CONSENTS[0], withdrawn_at: "2026-07-31T13:00:00Z", is_active: false },
      ACTIVE_CONSENTS[1],
    ]);
    render(<SettingsPage />);

    await screen.findByRole("heading", { name: "Your data and consent" });
    expect(screen.getByRole("link", { name: "Download .ics calendar" })).toHaveAttribute(
      "href",
      expect.stringContaining("/deadlines/calendar.ics"),
    );

    fireEvent.click(screen.getAllByRole("button", { name: "Withdraw" })[0]!);
    expect(screen.getByText(/permanently deletes your business profile/i)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Confirm withdrawal" }));

    await waitFor(() =>
      expect(mocks.updateConsent).toHaveBeenCalledWith("scheme_matching", false),
    );
    await waitFor(() =>
      expect(screen.queryByRole("link", { name: "Download .ics calendar" })).not.toBeInTheDocument(),
    );
    expect(screen.getByText(/Grant scheme matching and document-vault consent/i)).toBeVisible();
  });

  it("shows the deletion receipt returned by the API", async () => {
    mocks.eraseAccount.mockResolvedValue({
      account_deleted: true,
      profile_deleted: true,
      sessions_revoked: 2,
      consents_deleted: 2,
      ai_judgements_deleted: 3,
      applications_unlinked: 1,
      outcomes_retained_anonymised: 1,
      note: "Your personal data was deleted.",
    });
    render(<SettingsPage />);

    await screen.findByRole("button", { name: "Delete my account" });
    fireEvent.click(screen.getByRole("button", { name: "Delete my account" }));
    fireEvent.click(screen.getByRole("button", { name: "Permanently delete everything" }));

    await screen.findByRole("heading", { name: "Your account data was deleted" });
    expect(screen.getByText("3")).toBeVisible();
    expect(screen.getByText("Your personal data was deleted.")).toBeVisible();
  });
});
