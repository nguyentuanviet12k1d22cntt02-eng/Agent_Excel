import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

import { clearTokens } from "@/api/tokens";

afterEach(() => {
  cleanup();
  clearTokens();
  localStorage.clear();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});
