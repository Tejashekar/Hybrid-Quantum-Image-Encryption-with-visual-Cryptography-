export type Label = "A" | "B" | "C" | "D" | "E";
export interface ApiState {
  stage: string;
  label: Label | null;
  config: Record<string, unknown> | null;
  image: { original: string | null; processed: string | null; original_filename: string | null; original_dimensions: number[] | null; processed_shape: number[] | null; dtype: string | null };
  encrypted: string | null;
  reconstructed: string | null;
  decrypted: string | null;
  shares: { index: number; url: string; selected: boolean }[];
  metrics: Record<string, number | string | null> | null;
  threshold_verified: boolean | null;
  original: string | null; processed: string | null; encrypted_legacy: string | null; share1: string | null; share2: string | null; reconstructed_legacy: string | null; decrypted_legacy: string | null;
}
export const empty: ApiState = { stage: "idle", label: null, config: null, image: { original: null, processed: null, original_filename: null, original_dimensions: null, processed_shape: null, dtype: null }, encrypted: null, reconstructed: null, decrypted: null, shares: [], metrics: null, threshold_verified: null, original: null, processed: null, encrypted_legacy: null, share1: null, share2: null, reconstructed_legacy: null, decrypted_legacy: null };
async function request<T>(url: string, init?: RequestInit): Promise<T> { const response = await fetch(url, { ...init, credentials: "include" }); const body = await response.json(); if (!response.ok) throw new Error(body.error ?? "Request failed"); return body; }
export async function fetchState() { return request<ApiState>("/api/state"); }
export async function uploadImage(file: File) { const data = new FormData(); data.append("file", file); return request<{ message: string; state: ApiState }>("/api/upload", { method: "POST", body: data }); }
export async function encryptImage(configuration: Label, k = 2, n = 2) { return request<{ message: string; state: ApiState }>("/api/encrypt", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ configuration, k, n }) }); }
export async function reconstruct(indices: number[]) { return request<{ message: string; state: ApiState }>("/api/reconstruct", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ indices }) }); }
export async function fetchExperimentResults() { return request<{ rows: Record<string, unknown>[]; count: number }>("/api/experiment-results"); }
// Compatibility exports for the earlier section components retained in the repository.
export interface PipelineState { original: string | null; processed: string | null; encrypted: string | null; share1: string | null; share2: string | null; reconstructed: string | null; decrypted: string | null; }
export interface Metrics { entropy_encrypted: number; correlation_encrypted: number; npcr: number; uaci: number; psnr_original_vs_decrypted: number | string; }
export async function runEncrypt() { return encryptImage("D"); }
export async function runReconstruct(_share1?: File, _share2?: File) { void _share1; void _share2; return reconstruct([1, 2]); }
export async function fetchMetrics(): Promise<{ metrics: Metrics | null; state: PipelineState }> { const state = await fetchState(); return { metrics: state.metrics as Metrics | null, state: state as unknown as PipelineState }; }
export function outputUrl(filename: string) { return `/output/${filename}`; }
export function inputUrl(filename: string) { return `/input/${filename}`; }
