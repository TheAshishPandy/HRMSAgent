import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import SmartChat from "../components/SmartChat.vue";

vi.mock("../api", () => ({
  api: vi.fn(async (path, opts = {}) => {
    if (path === "/api/chat/context") {
      return { user_type: "employee", name: "Sam Lee", employee_id: "e1", organization_id: "o1" };
    }
    if (path === "/api/chat/conversations") return [];
    if (path === "/api/chat/messages") {
      return { conversation_id: "c1", reply: "Your current leave balance from the HR system is 8.", sources: [], cards: [], agents: ["employee_data"] };
    }
    return {};
  }),
}));

vi.mock("../stores/auth", () => ({
  auth: { user: { role: "employee", name: "Sam Lee" }, token: "t" },
}));

describe("SmartChat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("opens a panel that does not ask for employee id", async () => {
    const wrapper = mount(SmartChat);
    await flushPromises();
    await wrapper.find(".sc-fab").trigger("click");
    await flushPromises();
    const text = wrapper.text();
    expect(text).toContain("Smart Chat");
    expect(text.toLowerCase()).not.toContain("what is your employee id");
    expect(text).toContain("Employee");
  });
});
