import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  addDocument: vi.fn(),
  registerAccount: vi.fn(),
  saveProfile: vi.fn(),
}));

vi.mock("@/lib/api", () => api);

import {
  JUDGE_DEMO_DOCUMENTS,
  JUDGE_DEMO_PROFILE,
  provisionJudgeDemo,
} from "@/lib/demo";

describe("provisionJudgeDemo", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.registerAccount.mockResolvedValue({});
    api.saveProfile.mockResolvedValue({});
    api.addDocument.mockResolvedValue({});
  });

  it("creates an isolated account, saves Arjun's profile, and seeds his vault", async () => {
    await provisionJudgeDemo();

    expect(api.registerAccount).toHaveBeenCalledWith({
      email: expect.stringMatching(/^judge-.+@example\.com$/),
      password: expect.stringMatching(/^bharat-os-judge-.+/),
      consents: ["scheme_matching", "document_storage", "outcome_analytics"],
    });
    expect(api.saveProfile).toHaveBeenCalledWith(JUDGE_DEMO_PROFILE);
    expect(api.addDocument).toHaveBeenCalledTimes(JUDGE_DEMO_DOCUMENTS.length);
    for (const document of JUDGE_DEMO_DOCUMENTS) {
      expect(api.addDocument).toHaveBeenCalledWith(document);
    }
  });

  it("still opens the core demo when an optional vault write fails", async () => {
    api.addDocument.mockRejectedValueOnce(new Error("vault unavailable"));

    await expect(provisionJudgeDemo()).resolves.toBeUndefined();
    expect(api.saveProfile).toHaveBeenCalledWith(JUDGE_DEMO_PROFILE);
  });
});
