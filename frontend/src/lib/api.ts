// Shared types for the pipeline state & metrics coming from Flask
export interface PipelineState {
  original: string | null;
  processed: string | null;
  encrypted: string | null;
  share1: string | null;
  share2: string | null;
  reconstructed: string | null;
  decrypted: string | null;
}

export interface Metrics {
  entropy_encrypted: number;
  correlation_encrypted: number;
  npcr: number;
  uaci: number;
  psnr_original_vs_decrypted: number | string;
}

const BASE = ""; // proxied through next.config rewrites

export async function fetchState(): Promise<PipelineState> {
  const res = await fetch(`${BASE}/api/state`, { credentials: "include" });
  return res.json();
}

export async function uploadImage(file: File): Promise<{ message: string; state: PipelineState }> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${BASE}/api/upload`, {
    method: "POST",
    body: fd,
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error ?? "Upload failed");
  }
  return res.json();
}

export async function runEncrypt(): Promise<{ message: string; state: PipelineState }> {
  const res = await fetch(`${BASE}/api/encrypt`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error ?? "Encryption failed");
  }
  return res.json();
}

export async function runReconstruct(
  share1?: File,
  share2?: File,
): Promise<{ message: string; state: PipelineState }> {
  const fd = new FormData();
  if (share1) fd.append("share1", share1);
  if (share2) fd.append("share2", share2);
  const res = await fetch(`${BASE}/api/reconstruct`, {
    method: "POST",
    body: fd,
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error ?? "Reconstruction failed");
  }
  return res.json();
}

export async function fetchMetrics(): Promise<{ metrics: Metrics | null; state: PipelineState }> {
  const res = await fetch(`${BASE}/api/metrics`, { credentials: "include" });
  return res.json();
}

export function outputUrl(filename: string) {
  return `${BASE}/output/${filename}`;
}

export function inputUrl(filename: string) {
  return `${BASE}/input/${filename}`;
}
