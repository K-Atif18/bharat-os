import {
  addDocument,
  registerAccount,
  saveProfile,
  type ProfileInput,
  type UserDocumentInput,
} from "@/lib/api";

/**
 * The persona used in the three-minute judge flow.
 *
 * This is deliberately provisioned through the same authenticated APIs as a
 * real account. The demo is fast without creating a second, less secure code
 * path that could drift away from the product being judged.
 */
export const JUDGE_DEMO_PROFILE: ProfileInput = {
  entity_name: "ZEN Club",
  state: "Maharashtra",
  district: "Pune",
  sector: "logistics",
  stage: "early",
  employee_count: 12,
  incorporation_date: "2025-08-12",
  is_woman_led: false,
  registrations: ["dpiit", "gst", "company_incorporation"],
  annual_turnover_inr: 1_800_000,
  social_category: "general",
};

export const JUDGE_DEMO_DOCUMENTS: UserDocumentInput[] = [
  {
    document_type: "dpiit_certificate",
    label: "DPIIT recognition certificate",
    issuing_authority_name: "DPIIT",
    issue_date: "2025-09-02",
    expiry_date: null,
  },
  {
    document_type: "incorporation_certificate",
    label: "Certificate of incorporation",
    issuing_authority_name: "Ministry of Corporate Affairs",
    issue_date: "2025-08-12",
    expiry_date: null,
  },
  {
    document_type: "pan_card",
    label: "Company PAN",
    issuing_authority_name: "Income Tax Department",
    issue_date: "2025-08-20",
    expiry_date: null,
  },
];

export async function provisionJudgeDemo(): Promise<void> {
  const suffix = `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

  await registerAccount({
    email: `judge-${suffix}@example.com`,
    password: `bharat-os-judge-${suffix}`,
    consents: ["scheme_matching", "document_storage", "outcome_analytics"],
  });
  await saveProfile(JUDGE_DEMO_PROFILE);

  // Documents enrich the wow moment, but a transient failure here must not
  // block the real eligibility and drafting journey from loading.
  await Promise.allSettled(JUDGE_DEMO_DOCUMENTS.map((document) => addDocument(document)));
}
