import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import SlotPicker from "../components/SlotPicker.vue";

describe("SlotPicker", () => {
  it("disables Saturday and Sunday", () => {
    const wrapper = mount(SlotPicker, {
      props: {
        slots: [
          { start_at: "2026-09-04T15:00:00Z", end_at: "2026-09-04T15:45:00Z" },
          { start_at: "2026-09-05T15:00:00Z", end_at: "2026-09-05T15:45:00Z" },
          { start_at: "2026-09-06T15:00:00Z", end_at: "2026-09-06T15:45:00Z" },
        ],
      },
    });
    const buttons = wrapper.findAll("button");
    expect(buttons[0].attributes("disabled")).toBeUndefined();
    expect(buttons[1].attributes("disabled")).toBeDefined();
    expect(buttons[2].attributes("disabled")).toBeDefined();
  });
});
