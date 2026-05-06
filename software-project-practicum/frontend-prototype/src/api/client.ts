import { mockFetch } from "./mock-server";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";
const USE_MOCK = import.meta.env.VITE_USE_MOCK_API !== "false";

type ApiEnvelope<T> = {
  success: boolean;
  message?: string;
  data: T;
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type UnauthorizedHandler = () => void;

let unauthorizedHandler: UnauthorizedHandler | null = null;

export const setUnauthorizedHandler = (handler: UnauthorizedHandler) => {
  unauthorizedHandler = handler;
};

const createRequest = async (path: string, init?: RequestInit) => {
  const requestInit: RequestInit = {
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(init?.headers ?? {}),
    },
    credentials: "include",
    ...init,
  };

  const target = API_BASE ? `${API_BASE}${path}` : path;
  return USE_MOCK ? mockFetch(target, requestInit) : fetch(target, requestInit);
};

const isEnvelope = <T>(value: unknown): value is ApiEnvelope<T> =>
  typeof value === "object" && value !== null && "success" in value && "data" in value;

export const apiRequest = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await createRequest(path, init);
  const text = await response.text();
  const data = text ? (JSON.parse(text) as T | ApiEnvelope<T> | { message?: string }) : ({} as T);

  if (!response.ok) {
    const message = typeof data === "object" && data && "message" in data ? data.message ?? "请求失败。" : "请求失败。";
    if (response.status === 401) {
      unauthorizedHandler?.();
    }
    throw new ApiError(response.status, message);
  }

  if (isEnvelope<T>(data)) {
    if (!data.success) {
      throw new ApiError(response.status, data.message ?? "请求失败。");
    }
    return data.data;
  }

  return data as T;
};
