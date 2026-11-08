/**
 * Backend giả cho test: đăng ký trả lời theo phương thức + đường dẫn, ghi lại mọi yêu cầu đã gửi.
 * Cài bằng `installFakeApi()` (thay `fetch` toàn cục), không cần máy chủ thật.
 */
import { vi } from "vitest";

import type { Problem, User } from "@/api/types";

type Params = Record<string, string>;
type Reply = Response | object | null | undefined;
type Handler = (request: Request, params: Params, body: unknown) => Reply | Promise<Reply>;

interface Route {
  method: string;
  pattern: RegExp;
  keys: string[];
  handler: Handler;
}

export interface RecordedCall {
  method: string;
  path: string;
  search: string;
  body: unknown;
  authorization: string | null;
}

export function json(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

export function problem(status: number, code: string, message: string, errors?: Problem["errors"]): Response {
  return new Response(JSON.stringify({ code, message, errors }), {
    status,
    headers: { "Content-Type": "application/problem+json" },
  });
}

export const noContent = (): Response => new Response(null, { status: 204 });

async function readBody(request: Request): Promise<unknown> {
  const type = request.headers.get("Content-Type") ?? "";
  if (type.includes("multipart/form-data")) return request.formData();
  const text = await request.text();
  if (!text) return undefined;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

export class FakeApi {
  readonly calls: RecordedCall[] = [];
  private readonly routes: Route[] = [];

  on(method: string, path: string, handler: Handler | Reply): this {
    const keys: string[] = [];
    const source = path.replace(/:([a-z_]+)/g, (_, key: string) => {
      keys.push(key);
      return "([^/]+)";
    });
    const reply: Handler = typeof handler === "function" ? (handler as Handler) : () => handler;
    // Đăng ký sau được ưu tiên: test ghi đè trả lời mặc định
    this.routes.unshift({ method, pattern: new RegExp(`^/api/v1${source}$`), keys, handler: reply });
    return this;
  }

  callsTo(method: string, path: string): RecordedCall[] {
    return this.calls.filter((c) => c.method === method && c.path === `/api/v1${path}`);
  }

  readonly fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : new Request(input, init);
    const url = new URL(request.url);
    const body = await readBody(request.clone());
    this.calls.push({
      method: request.method,
      path: url.pathname,
      search: url.search,
      body,
      authorization: request.headers.get("Authorization"),
    });
    for (const route of this.routes) {
      const match = route.pattern.exec(url.pathname);
      if (route.method !== request.method || !match) continue;
      const params = Object.fromEntries(route.keys.map((key, i) => [key, decodeURIComponent(match[i + 1]!)]));
      const reply = await route.handler(request, params, body);
      if (reply instanceof Response) return reply;
      return reply === undefined || reply === null ? new Response(null, { status: 204 }) : json(reply);
    }
    return problem(404, "not_found", `Test chưa khai báo ${request.method} ${url.pathname}`);
  };
}

export const TEACHER: User = {
  id: "00000000-0000-4000-8000-000000000001",
  email: "gv@tdmu.edu.vn",
  full_name: "Giảng Viên A",
  role: "teacher",
  is_active: true,
};

export const ADMIN: User = { ...TEACHER, id: "00000000-0000-4000-8000-000000000002", role: "admin" };

/** Backend giả có sẵn đăng nhập: mật khẩu đúng là "matkhau123". */
export function installFakeApi(user: User = TEACHER): FakeApi {
  const api = new FakeApi();
  let issued = 0;
  const tokens = () => {
    issued += 1;
    return { access_token: `access-${issued}`, refresh_token: `refresh-${issued}`, expires_in: 3600 };
  };
  api
    .on("POST", "/auth/login", (_req, _params, body) => {
      const { password } = body as { password: string };
      if (password !== "matkhau123") return problem(401, "invalid_credentials", "Sai email hoặc mật khẩu");
      return tokens();
    })
    .on("POST", "/auth/refresh", () => tokens())
    .on("GET", "/auth/me", user);
  vi.stubGlobal("fetch", api.fetch);
  return api;
}
