export class ApiResponseError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiResponseError";
  }
}

interface RawApiError {
  code: string;
  message: string;
}

interface RawFastApiError {
  detail?: RawApiError | string;
}

function isRawApiError(value: unknown): value is RawApiError {
  return (
    typeof value === "object" &&
    value !== null &&
    "code" in value &&
    "message" in value &&
    typeof value.code === "string" &&
    typeof value.message === "string"
  );
}

function parseApiError(body: unknown, statusCode: number): RawApiError {
  if (isRawApiError(body)) {
    return body;
  }

  const detail = (body as RawFastApiError).detail;
  if (isRawApiError(detail)) {
    return detail;
  }
  if (typeof detail === "string") {
    return { code: "UNKNOWN", message: detail };
  }
  return { code: "UNKNOWN", message: `HTTP ${statusCode}` };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });

  if (!response.ok) {
    let errorBody: unknown;
    try {
      errorBody = await response.json();
    } catch {
      throw new ApiResponseError("UNKNOWN", `HTTP ${response.status}`);
    }
    const parsedError = parseApiError(errorBody, response.status);
    throw new ApiResponseError(parsedError.code, parsedError.message);
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PUT",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PATCH",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
