import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import OnboardingView from "../views/OnboardingView.vue";

const api = vi.fn();

vi.mock("../api", () => ({
  api: (...args) => api(...args),
}));

vi.mock("../stores/auth", () => ({
  auth: { user: { role: "hr", name: "Pat HR" }, token: "t" },
}));

describe("OnboardingView", () => {
  beforeEach(() => {
    api.mockReset();
    api.mockImplementation(async (path) => {
      if (path === "/api/onboarding") {
        return [{
          id: "o1",
          employee_name: "Eli Ng",
          employee_email: "eli@example.com",
          job_title: "Backend Engineer",
          designation: "SWE",
          joining_date: "2026-10-01",
          completed_tasks: 1,
          tasks_total: 5,
          status: "active",
          tasks: [{ id: "t1", title: "Offer letter signed", category: "contracts", completed: true }],
        }];
      }
      if (path === "/api/onboarding/eligible") {
        return [{
          application_id: "a1",
          candidate_name: "Ada Lovelace",
          candidate_email: "ada@example.com",
          job_title: "Backend Engineer",
        }];
      }
      return [];
    });
  });

  it("lists eligible hires and in-progress onboarding for HR", async () => {
    const wrapper = mount(OnboardingView);
    await flushPromises();
    const text = wrapper.text();
    expect(text).toContain("Ready to onboard");
    expect(text).toContain("Ada Lovelace");
    expect(text).toContain("Start onboarding");
    expect(text).toContain("Eli Ng");
    expect(text).toContain("1/5");
  });
});
