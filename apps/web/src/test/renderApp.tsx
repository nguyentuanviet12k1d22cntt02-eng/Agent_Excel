import { render, type RenderResult } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";

import { Providers } from "@/app/Providers";
import { createQueryClient } from "@/app/queryClient";
import { routes } from "@/app/routes";
import { saveTokens } from "@/api/tokens";

/** Đặt sẵn phiên đăng nhập như khi người dùng đã đăng nhập từ trước. */
export function signIn(): void {
  saveTokens({ access_token: "access-0", refresh_token: "refresh-0", expires_in: 3600 });
}

/** Dựng cả ứng dụng (đủ định tuyến, provider) tại một đường dẫn. */
export function renderApp(path = "/"): RenderResult & { router: ReturnType<typeof createMemoryRouter> } {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const client = createQueryClient();
  client.setDefaultOptions({ queries: { ...client.getDefaultOptions().queries, retry: false } });
  const result = render(
    <Providers client={client}>
      <RouterProvider router={router} />
    </Providers>,
  );
  return { ...result, router };
}
