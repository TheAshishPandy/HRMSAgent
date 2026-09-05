import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import PublicJobDetailView from "../views/PublicJobDetailView.vue";

vi.mock("../api", () => ({
  api: vi.fn(async (path) => {
    if (path.startsWith("/api/jobs/") && !path.endsWith("/apply")) {
      return { id: "j1", title: "Backend", jd_markdown: "# Backend" };
    }
    return { status: "applied" };
  }),
}));

describe("Apply form", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  it("requires a resume file", async () => {
    const wrapper = mount(PublicJobDetailView, {
      global: {
        mocks: { $route: { params: { id: "j1" } } },
        stubs: { RouterLink: true },
      },
    });
    await flushPromises();
    await wrapper.find("form").trigger("submit");
    expect(wrapper.text()).toContain("Please attach a resume file");
  });
});
