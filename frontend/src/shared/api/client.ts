import { z } from "zod";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";
const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

export class ApiError extends Error {
  statusCode?: number;

  constructor(message: string, statusCode?: number) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
  }
}

export function withQuery<T extends object>(url: string, params?: T) {
  const search = new URLSearchParams();

  Object.entries((params ?? {}) as Record<string, unknown>).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  });

  return search.size ? `${url}?${search.toString()}` : url;
}

export async function apiRequest<T>({
  path,
  init,
  schema,
  mockData
}: {
  path: string;
  init?: RequestInit;
  schema?: z.ZodSchema<T>;
  mockData?: T;
}): Promise<T> {
  if (USE_MOCKS && mockData !== undefined) {
    return mockData;
  }

  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {})
      },
      cache: "no-store"
    });
  } catch (error) {
    throw new ApiError(`Network error while requesting ${path}. ${error instanceof Error ? error.message : ""}`.trim());
  }

  let payload: unknown = null;

  try {
    payload = await response.json();
  } catch {
    throw new ApiError(`Invalid JSON returned from ${path}.`, response.status);
  }

  if (!response.ok) {
    const message =
      typeof payload === "object" && payload && "error" in payload && typeof payload.error === "string"
        ? payload.error
        : `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status);
  }

  if (!schema) {
    return payload as T;
  }

  const parsed = schema.safeParse(payload);

  if (!parsed.success) {
    throw new ApiError(`Response validation failed for ${path}: ${parsed.error.issues[0]?.message ?? "unknown error"}`);
  }

  return parsed.data;
}

export { API_BASE_URL, USE_MOCKS };
