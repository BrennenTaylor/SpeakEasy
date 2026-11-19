export type HealthResponse = { status: "ok" };

export class ApiError extends Error {
  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = "ApiError";
  }
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const HEALTH_TIMEOUT_MS = 8_000;

function isTimeout(cause: unknown): boolean {
  return (
    typeof cause === "object" &&
    cause !== null &&
    "name" in cause &&
    (cause as { name?: unknown }).name === "TimeoutError"
  );
}

function isHealthResponse(value: unknown): value is HealthResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    "status" in value &&
    (value as { status: unknown }).status === "ok"
  );
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const timeoutSignal = AbortSignal.timeout(HEALTH_TIMEOUT_MS);
  const requestSignal = signal ? AbortSignal.any([signal, timeoutSignal]) : timeoutSignal;
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/api/health`, {
      signal: requestSignal,
      headers: { accept: "application/json" },
    });
  } catch (cause) {
    if (isTimeout(cause)) {
      throw new ApiError("Server did not respond", { cause });
    }
    throw new ApiError("Could not reach the server", { cause });
  }
  if (!response.ok) {
    throw new ApiError(`Server responded with ${response.status}`);
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch (cause) {
    throw new ApiError("Server returned a response that was not JSON", { cause });
  }
  if (!isHealthResponse(body)) {
    throw new ApiError("Server returned an unexpected response");
  }
  return body;
}
