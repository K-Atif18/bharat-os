import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiBaseUrl, getScheme, listSchemes } from "@/lib/api";

function mockFetch(response: Partial<Response> & { json?: () => Promise<unknown> }) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    statusText: "OK",
    json: async () => [],
    ...response,
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("apiBaseUrl", () => {
  it("uses the browser hostname when no API URL is configured", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_API_PORT", "8000");

    expect(apiBaseUrl()).toBe(
      `${window.location.protocol}//${window.location.hostname}:8000`,
    );
  });

  it("prefers an explicit API URL and removes its trailing slash", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.test/");

    expect(apiBaseUrl()).toBe("https://api.example.test");
  });
});

describe("listSchemes", () => {
  it("omits the query string when no filters are given", async () => {
    const fetchMock = mockFetch({ json: async () => [] });
    await listSchemes();
    expect(fetchMock.mock.calls[0]?.[0]).toMatch(/\/schemes$/);
  });

  it("passes filters through as query parameters", async () => {
    const fetchMock = mockFetch({ json: async () => [] });
    await listSchemes({ segment: "msme", state: "Maharashtra" });
    const url = String(fetchMock.mock.calls[0]?.[0]);
    expect(url).toContain("segment=msme");
    expect(url).toContain("state=Maharashtra");
  });

  it("never serves cached scheme data", async () => {
    // Stale scheme data is actively harmful: an applicant could work against
    // criteria that have since been amended.
    const fetchMock = mockFetch({ json: async () => [] });
    await listSchemes();
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ cache: "no-store" });
  });
});

describe("getScheme", () => {
  it("encodes the slug", async () => {
    const fetchMock = mockFetch({ json: async () => ({}) });
    await getScheme("a b/c");
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("/schemes/a%20b%2Fc");
  });

  it("requests a specific version when asked", async () => {
    const fetchMock = mockFetch({ json: async () => ({}) });
    await getScheme("sisfs", 2);
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("?version=2");
  });

  it("surfaces the API detail message on failure", async () => {
    mockFetch({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({ detail: "No scheme found for slug 'nope'" }),
    });
    await expect(getScheme("nope")).rejects.toThrowError(ApiError);
    await expect(getScheme("nope")).rejects.toThrow(/No scheme found/);
  });

  it("falls back to status text when the error body is not JSON", async () => {
    mockFetch({
      ok: false,
      status: 502,
      statusText: "Bad Gateway",
      json: async () => {
        throw new Error("not json");
      },
    });
    await expect(getScheme("nope")).rejects.toThrow(/Bad Gateway/);
  });
});
