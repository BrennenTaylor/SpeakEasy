const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const DEFAULT_TIMEOUT_MS = 8_000;

export class RequestError extends Error {
  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = "RequestError";
  }
}

function isTimeout(cause: unknown): boolean {
  return (
    typeof cause === "object" &&
    cause !== null &&
    "name" in cause &&
    (cause as { name?: unknown }).name === "TimeoutError"
  );
}

export async function requestJson<T>(
  path: string,
  init: RequestInit,
  validate: (value: unknown) => value is T,
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const timeoutSignal = AbortSignal.timeout(timeoutMs);
  const requestSignal = init.signal ? AbortSignal.any([init.signal, timeoutSignal]) : timeoutSignal;
  const headers: Record<string, string> = {
    accept: "application/json",
    ...(init.body === undefined || init.body === null
      ? {}
      : { "content-type": "application/json" }),
    ...((init.headers ?? {}) as Record<string, string>),
  };

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { ...init, headers, signal: requestSignal });
  } catch (cause) {
    if (isTimeout(cause)) {
      throw new RequestError("Server did not respond", { cause });
    }
    throw new RequestError("Could not reach the server", { cause });
  }
  if (!response.ok) {
    throw new RequestError(`Server responded with ${response.status}`);
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch (cause) {
    throw new RequestError("Server returned a response that was not JSON", { cause });
  }
  if (!validate(body)) {
    throw new RequestError("Server returned an unexpected response");
  }
  return body;
}
