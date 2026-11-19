import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, fetchHealth } from "../api/health";

type HealthState = { kind: "loading" } | { kind: "ok" } | { kind: "error"; message: string };

export function HealthCheck() {
  const [state, setState] = useState<HealthState>({ kind: "loading" });
  const activeControllerRef = useRef<AbortController | null>(null);

  const runCheck = useCallback(() => {
    activeControllerRef.current?.abort();
    const controller = new AbortController();
    activeControllerRef.current = controller;

    fetchHealth(controller.signal)
      .then(() => {
        if (!controller.signal.aborted) {
          setState({ kind: "ok" });
        }
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        if (error instanceof ApiError) {
          setState({ kind: "error", message: error.message });
        } else {
          setState({ kind: "error", message: "Something went wrong" });
        }
      });
  }, []);

  useEffect(() => {
    void runCheck();
    return () => {
      activeControllerRef.current?.abort();
      activeControllerRef.current = null;
    };
  }, [runCheck]);

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
          setState({ kind: "loading" });
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
