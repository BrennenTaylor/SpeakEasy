import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, fetchHealth } from "../api/health";

type HealthState = { kind: "loading" } | { kind: "ok" } | { kind: "error"; message: string };

function isAbortError(error: unknown): boolean {
  if (!(error instanceof Error)) {
    return false;
  }
  if (error.name === "AbortError") {
    return true;
  }
  const cause = error.cause;
  if (cause instanceof Error && cause.name === "AbortError") {
    return true;
  }
  if (
    typeof cause === "object" &&
    cause !== null &&
    "name" in cause &&
    (cause as { name?: unknown }).name === "AbortError"
  ) {
    return true;
  }
  return false;
}

export function HealthCheck() {
  const [state, setState] = useState<HealthState>({ kind: "loading" });
  const activeControllerRef = useRef<AbortController | null>(null);

  const runCheck = useCallback(async () => {
    activeControllerRef.current?.abort();
    const controller = new AbortController();
    activeControllerRef.current = controller;
    setState({ kind: "loading" });

    try {
      await fetchHealth(controller.signal);
      if (controller.signal.aborted) {
        return;
      }
      setState({ kind: "ok" });
    } catch (error) {
      if (controller.signal.aborted || isAbortError(error)) {
        return;
      }
      if (error instanceof ApiError) {
        setState({ kind: "error", message: error.message });
      } else {
        setState({ kind: "error", message: "Something went wrong" });
      }
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    activeControllerRef.current = controller;

    fetchHealth(controller.signal)
      .then(() => {
        if (!cancelled && !controller.signal.aborted) {
          setState({ kind: "ok" });
        }
      })
      .catch((error: unknown) => {
        if (cancelled || controller.signal.aborted || isAbortError(error)) {
          return;
        }
        if (error instanceof ApiError) {
          setState({ kind: "error", message: error.message });
        } else {
          setState({ kind: "error", message: "Something went wrong" });
        }
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  const isChecking = state.kind === "loading";

  return (
    <div
      role={state.kind === "error" ? "alert" : "status"}
      className={`flex items-center justify-between gap-3 rounded-lg border p-3 text-sm break-words ${
        state.kind === "error"
          ? "border-red-200 bg-red-50 text-red-900"
          : "border-gray-200 bg-white text-gray-900"
      }`}
    >
      <span className="min-w-0 flex-1 break-words">
        {state.kind === "loading" && "Checking…"}
        {state.kind === "ok" && "Connected"}
        {state.kind === "error" && state.message}
      </span>
      <button
        type="button"
        onClick={() => {
          void runCheck();
        }}
        disabled={isChecking}
        className="shrink-0 rounded border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Try again
      </button>
    </div>
  );
}
