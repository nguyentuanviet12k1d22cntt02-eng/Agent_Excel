import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router";

import { Providers } from "@/app/Providers";
import { createQueryClient } from "@/app/queryClient";
import { routes } from "@/app/routes";

import "@/app/styles.css";

const root = document.getElementById("root");
if (!root) throw new Error("Thiếu phần tử #root trong index.html");

createRoot(root).render(
  <StrictMode>
    <Providers client={createQueryClient()}>
      <RouterProvider router={createBrowserRouter(routes)} />
    </Providers>
  </StrictMode>,
);
