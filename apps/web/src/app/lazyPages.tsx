import { lazy } from "react";

// Trình sửa kịch bản kéo theo bộ kiểm lược đồ (Ajv): tải riêng khi mở, các trang khác nhẹ hơn
export const ScriptEditorPage = lazy(() =>
  import("@/features/script-editor/ScriptEditorPage").then((m) => ({ default: m.ScriptEditorPage })),
);
