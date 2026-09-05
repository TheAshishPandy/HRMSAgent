import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import PipelineBoard from "../components/PipelineBoard.vue";

describe("PipelineBoard", () => {
  it("renders five column headers", () => {
    const wrapper = mount(PipelineBoard, {
      props: {
        apps: [
          { id: "1", status: "applied", candidate_name: "Ada", keyword_score: 0.7 },
          { id: "2", status: "screened", candidate_name: "Bob", keyword_score: 0.9 },
        ],
      },
    });
    const text = wrapper.text();
    for (const h of ["Applied", "Screened", "Interview", "Offer", "Rejected"]) {
      expect(text).toContain(h);
    }
  });
});
