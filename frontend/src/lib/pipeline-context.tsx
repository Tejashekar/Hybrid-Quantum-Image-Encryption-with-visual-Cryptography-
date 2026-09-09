"use client";
import React, { createContext, useContext, useState, useCallback } from "react";
import type { PipelineState, Metrics } from "@/lib/api";
import { fetchState, fetchMetrics as apiFetchMetrics } from "@/lib/api";

interface Ctx {
  state: PipelineState;
  metrics: Metrics | null;
  refresh: () => Promise<void>;
  refreshMetrics: () => Promise<void>;
  setState: React.Dispatch<React.SetStateAction<PipelineState>>;
}

const empty: PipelineState = {
  original: null,
  processed: null,
  encrypted: null,
  share1: null,
  share2: null,
  reconstructed: null,
  decrypted: null,
};

const PipelineContext = createContext<Ctx>({
  state: empty,
  metrics: null,
  refresh: async () => {},
  refreshMetrics: async () => {},
  setState: () => {},
});

export const usePipeline = () => useContext(PipelineContext);

export function PipelineProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<PipelineState>(empty);
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  const refresh = useCallback(async () => {
    try {
      const s = await fetchState();
      setState(s);
    } catch {
      /* backend offline */
    }
  }, []);

  const refreshMetrics = useCallback(async () => {
    try {
      const { metrics: m, state: s } = await apiFetchMetrics();
      setMetrics(m);
      setState(s);
    } catch {
      /* backend offline */
    }
  }, []);

  return (
    <PipelineContext.Provider value={{ state, metrics, refresh, refreshMetrics, setState }}>
      {children}
    </PipelineContext.Provider>
  );
}
