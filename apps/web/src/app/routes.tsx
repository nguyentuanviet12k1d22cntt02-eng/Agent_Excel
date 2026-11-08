import { Suspense } from "react";
import type { RouteObject } from "react-router";

import { Loading } from "@/components/Loading";

import { LoginPage } from "@/features/auth/LoginPage";
import { RequireAuth } from "@/features/auth/RequireAuth";
import { ExerciseCreatePage } from "@/features/materials/ExerciseCreatePage";
import { ExerciseDetailPage } from "@/features/materials/ExerciseDetailPage";
import { ExercisesPage } from "@/features/materials/ExercisesPage";
import { TextbooksPage } from "@/features/materials/TextbooksPage";

import { HomePage } from "./HomePage";
import { Layout } from "./Layout";
import { ScriptEditorPage } from "./lazyPages";
import { NotFoundPage } from "./NotFoundPage";

export interface RouteHandle {
  wide?: boolean; // trang cần cả bề ngang màn hình (trình sửa kịch bản)
}

export const routes: RouteObject[] = [
  { path: "/login", element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <Layout />,
        children: [
          { index: true, element: <HomePage /> },
          { path: "exercises", element: <ExercisesPage /> },
          { path: "exercises/new", element: <ExerciseCreatePage /> },
          { path: "exercises/:exerciseId", element: <ExerciseDetailPage /> },
          { path: "textbooks", element: <TextbooksPage /> },
          {
            path: "scripts/:versionId",
            element: (
              <Suspense fallback={<Loading />}>
                <ScriptEditorPage />
              </Suspense>
            ),
            handle: { wide: true } satisfies RouteHandle,
          },
          { path: "*", element: <NotFoundPage /> },
        ],
      },
    ],
  },
];
