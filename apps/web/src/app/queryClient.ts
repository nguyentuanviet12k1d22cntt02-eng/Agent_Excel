import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "@/api/errors";

/** Lỗi do dữ liệu/quyền (4xx) thì gọi lại cũng vậy: không thử lại. Lỗi mạng, 5xx thử lại một lần. */
function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status < 500) return false;
  return failureCount < 1;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetry, staleTime: 10_000, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  });
}
