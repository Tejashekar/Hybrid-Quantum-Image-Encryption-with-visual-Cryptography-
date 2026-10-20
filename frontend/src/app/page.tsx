"use client";

import Image from "next/image";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, DragEvent, ReactNode } from "react";
import {
  Activity, ArrowDown, ArrowRight, Atom, Check, CircleHelp,
  Cpu, Database, FileImage, FlaskConical, Gauge, GitBranch, ImagePlus,
  Layers3, LockKeyhole, Menu, Network, RefreshCw, Shield, Sparkles,
  UploadCloud, Waves, X,
} from "lucide-react";
import {
  empty, encryptImage, fetchExperimentResults, fetchState, reconstruct,
  uploadImage, type ApiState, type Label,
} from "@/lib/api";

const configurations: { id: Label; name: string; description: string; path: string }[] = [
  { id: "A", name: "Classical XOR", description: "Classical baseline for comparison.", path: "Preprocess → XOR" },
  { id: "B", name: "Chaotic Key + XOR", description: "Logistic chaotic key with XOR diffusion.", path: "Preprocess → Logistic key → XOR" },
  { id: "C", name: "Quantum-Inspired + XOR", description: "Classical reversible bit-level transform.", path: "Preprocess → Quantum-inspired transform → XOR" },
  { id: "D", name: "Full Hybrid", description: "Combined chaotic and reversible transforms.", path: "Logistic key → Arnold → Quantum-inspired → XOR" },
  { id: "E", name: "Hybrid + Threshold Sharing", description: "D followed by GF(2^8)-based threshold secret sharing.", path: "Full hybrid → k-of-n shares" },
];
const thresholds = [[2, 2], [2, 3], [3, 5], [3, 6]] as const;
const pipelineByConfiguration: Record<Label, string[]> = {
  A: ["Input", "Preprocessing", "Classical XOR", "Encrypted output"],
  B: ["Input", "Preprocessing", "Chaotic key", "XOR diffusion", "Encrypted output"],
  C: ["Input", "Preprocessing", "Quantum-inspired transform", "XOR diffusion", "Encrypted output"],
  D: ["Input", "Preprocessing", "Chaotic key", "Arnold scrambling", "Quantum-inspired transform", "XOR diffusion", "Encrypted output"],
  E: ["Input", "Preprocessing", "Chaotic key", "Arnold scrambling", "Quantum-inspired transform", "XOR diffusion", "Encrypted output", "Threshold sharing"],
};

function display(value: unknown, digits = 4) {
  if (value === null || value === undefined) return "N/A";
  if (value === "inf" || value === Infinity) return "\u221e";
  if (typeof value === "number") return Number.isFinite(value) ? value.toFixed(digits) : "N/A";
  return String(value);
}

function numeric(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export default function Home() {
  const [state, setState] = useState<ApiState>(empty);
  const [configuration, setConfiguration] = useState<Label>("D");
  const [threshold, setThreshold] = useState<[number, number]>([2, 3]);
  const [selectedShares, setSelectedShares] = useState<number[]>([]);
  const [operation, setOperation] = useState<"upload" | "encrypt" | "reconstruct" | "">("");
  const [dragging, setDragging] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [apiReady, setApiReady] = useState<boolean | null>(null);
  const [error, setError] = useState("");
  const [results, setResults] = useState<Record<string, unknown>[]>([]);
  const [resultsLoaded, setResultsLoaded] = useState(false);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [resultsError, setResultsError] = useState("");
  const [showAllResults, setShowAllResults] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const stages = pipelineByConfiguration[configuration];
  const requiredShares = threshold[0];
  const activeConfigurationMatches = state.label === configuration;
  const backendThreshold = state.config?.threshold as { k?: number; n?: number } | undefined;
  const matchingShareSet = configuration === "E" && state.label === "E"
    && backendThreshold?.k === threshold[0] && backendThreshold?.n === threshold[1];
  const canDecryptDirectly = configuration !== "E" && activeConfigurationMatches && Boolean(state.encrypted);

  useEffect(() => {
    fetchState().then((current) => {
      setState(current);
      setApiReady(true);
      if (current.label) setConfiguration(current.label);
      const savedThreshold = (current.config?.threshold ?? {}) as { k?: number; n?: number };
      if (current.label === "E" && savedThreshold.k && savedThreshold.n) {
        setThreshold([savedThreshold.k, savedThreshold.n]);
      }
    }).catch(() => {
      setApiReady(false);
      setError("The research API is unavailable. Start Flask on port 5000 and retry.");
    });
  }, []);

  const receiveImage = useCallback(async (file?: File) => {
    if (!file) return;
    setError("");
    setSelectedShares([]);
    setOperation("upload");
    try {
      const response = await uploadImage(file);
      setState(response.state);
      setApiReady(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to process the selected image.");
    } finally {
      setOperation("");
    }
  }, []);

  const encrypt = useCallback(async () => {
    setError("");
    setSelectedShares([]);
    setOperation("encrypt");
    try {
      const response = await encryptImage(configuration, threshold[0], threshold[1]);
      setState(response.state);
      setApiReady(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Encryption failed. See diagnostic details.");
    } finally {
      setOperation("");
    }
  }, [configuration, threshold]);

  const decrypt = useCallback(async () => {
    if (configuration === "E" && selectedShares.length < requiredShares) return;
    setError("");
    setOperation("reconstruct");
    try {
      const response = await reconstruct(configuration === "E" ? selectedShares : []);
      setState(response.state);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Reconstruction failed. See diagnostic details.");
    } finally {
      setOperation("");
    }
  }, [configuration, requiredShares, selectedShares]);

  const loadResults = useCallback(async () => {
    setResultsError("");
    setResultsLoading(true);
    try {
      const response = await fetchExperimentResults();
      setResults(response.rows);
      setResultsLoaded(true);
    } catch (cause) {
      setResultsError(cause instanceof Error ? cause.message : "Unable to load experiment results.");
    } finally {
      setResultsLoading(false);
    }
  }, []);

  const successfulResults = results.filter((row) => String(row.status).toLowerCase() === "success").length;
  const failedResults = results.filter((row) => String(row.status).toLowerCase() === "failure").length;
  const visibleResults = showAllResults ? results : results.slice(0, 12);

  const metrics = state.metrics;
  const metricCards = useMemo(() => [
    ["Shannon entropy", metrics?.entropy, "bits / pixel", "entropy"],
    ["Horizontal correlation", metrics?.correlation_horizontal, "Pearson r", "correlation"],
    ["Vertical correlation", metrics?.correlation_vertical, "Pearson r", "correlation"],
    ["Diagonal correlation", metrics?.correlation_diagonal, "Pearson r", "correlation"],
    ["NPCR", metrics?.npcr, "%", "differential"],
    ["UACI", metrics?.uaci, "%", "differential"],
    ["MSE", metrics?.mse, "pixel error", "recovery"],
    ["PSNR", metrics?.psnr, "dB", "recovery"],
    ["SSIM", metrics?.ssim, "similarity", "recovery"],
  ] as const, [metrics]);

  const uploadFromDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    void receiveImage(event.dataTransfer.files[0]);
  };

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#home" aria-label="Q-CRYPT home">
          <span className="brand-mark"><Sparkles size={17} strokeWidth={1.8} /></span>
          <span>Q-CRYPT</span>
        </a>
        <nav className={`navigation ${menuOpen ? "navigation-open" : ""}`} aria-label="Main navigation">
          {[
            ["Encryption Lab", "#lab"], ["Pipeline", "#pipeline"], ["Security", "#security"],
            ["Threshold Sharing", "#sharing"], ["Experiments", "#experiments"], ["Methodology", "#methodology"],
          ].map(([label, href]) => (
            <a href={href} key={href} onClick={() => setMenuOpen(false)}>{label}</a>
          ))}
        </nav>
        <div className="topbar-end">
          <span className={`system-status ${apiReady === false ? "status-offline" : ""}`}>
            <i />{apiReady === false ? "API OFFLINE" : apiReady ? "SYSTEM READY" : "CONNECTING"}
          </span>
          <button className="mobile-menu" onClick={() => setMenuOpen((open) => !open)} aria-expanded={menuOpen} aria-label="Toggle navigation">
            {menuOpen ? <X size={19} /> : <Menu size={19} />}
          </button>
        </div>
      </header>

      <section className="hero page-shell" id="home">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-line" />RESEARCH FRAMEWORK <span className="eyebrow-index">01 / 06</span></div>
          <h1>Encrypt.<br />Distribute.<br /><em>Reconstruct.</em></h1>
          <p className="hero-subtitle">Quantum-Inspired Image Encryption &amp; Threshold Secret Sharing</p>
          <p className="hero-description">A configurable hybrid research framework for reversible image transformations, threshold reconstruction, and systematic security and resource analysis.</p>
          <div className="hero-actions">
            <a className="button button-primary" href="#lab">Launch Encryption Lab <ArrowRight size={16} /></a>
            <a className="button button-quiet" href="#methodology">Explore Methodology <ArrowDown size={15} /></a>
          </div>
          <div className="hero-footnote"><span className="mini-led" />Classical simulation of quantum-inspired transformations</div>
        </div>
        <div className="hero-art" aria-label="Abstract visualization of image data transformation">
          <div className="art-heading"><span>TRANSFORM SEQUENCE</span><span>128 <b>x</b> 128</span></div>
          <div className="art-grid" aria-hidden="true">{Array.from({ length: 100 }, (_, index) => <i key={index} style={{ "--tile-alpha": 0.12 + ((index * 17 + (index % 9) * 13) % 73) / 180 } as CSSProperties} />)}</div>
          <div className="art-flow" aria-hidden="true"><span>PIXEL FIELD</span><b /><span>REVERSIBLE MAP</span><b /><span>CIPHER</span></div>
          <div className="art-tag tag-top"><Activity size={13} /> CLASSICAL WORKFLOW</div>
          <div className="art-tag tag-bottom"><Waves size={13} /> DATA STATE / ACTIVE</div>
        </div>
      </section>

      <section className="lab-section page-shell section-block" id="lab">
        <SectionHeading index="02 / LAB" title={<>Configure an<br /><em>encryption run.</em></>} detail="Upload a visual input, select a research configuration, and inspect outputs returned by the Python pipeline." />
        <div className="lab-layout glass-panel">
          <div className="lab-input-column">
            <div className="column-heading"><span className="section-icon"><ImagePlus size={16} /></span><div><span className="micro-label">01 — IMAGE INPUT</span><h3>Source image</h3></div></div>
            <div className={`upload-zone ${dragging ? "upload-zone-dragging" : ""} ${state.image.original ? "has-image" : ""}`}
              role="button" tabIndex={0} aria-label="Choose or drop an image to upload"
              onClick={() => inputRef.current?.click()}
              onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); inputRef.current?.click(); } }}
              onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)} onDrop={uploadFromDrop}>
              <input ref={inputRef} className="visually-hidden" type="file" accept="image/png,image/jpeg,image/bmp,image/tiff" aria-label="Select an image to upload" onChange={(event) => void receiveImage(event.target.files?.[0])} />
              {state.image.original ? <Image src={state.image.original} alt="Uploaded source image preview" fill sizes="(max-width: 780px) 90vw, 340px" unoptimized className="upload-preview" /> : <div className="upload-empty"><span className="upload-icon"><UploadCloud size={21} /></span><strong>Drag an image into this area</strong><span>PNG, JPG, BMP, or TIFF · up to 10 MB</span></div>}
              {operation === "upload" && <div className="image-overlay"><RefreshCw className="spin" size={19} /> Preprocessing image</div>}
            </div>
            <button className="button button-secondary browse-button" onClick={() => inputRef.current?.click()} disabled={Boolean(operation)}><FileImage size={15} /> Browse Image</button>
            {state.image.original_filename && <div className="image-meta"><span className="file-dot" /><span className="file-name" title={state.image.original_filename}>{state.image.original_filename}</span><span className="file-state">{operation === "upload" ? "PROCESSING" : "READY"}</span></div>}
            <div className="image-facts">
              <Fact label="SOURCE DIMENSIONS" value={state.image.original_dimensions?.join(" x ") ?? "—"} />
              <Fact label="PROCESSED" value={state.image.processed_shape?.join(" x ") ?? "128 x 128"} />
              <Fact label="FORMAT" value={state.image.dtype ?? "Grayscale · uint8"} />
            </div>
            <p className="preprocess-note"><Check size={13} /> Preprocessing status: {state.image.processed ? "grayscale uint8 ready" : "awaiting image"}</p>
          </div>

          <div className="lab-config-column">
            <div className="column-heading"><span className="section-icon violet-icon"><Cpu size={16} /></span><div><span className="micro-label">02 — CONFIGURATION</span><h3>Choose a pipeline</h3></div></div>
            <div className="configuration-list" role="group" aria-label="Encryption configuration">
              {configurations.map((item) => (
                <button key={item.id} className={`configuration-card ${configuration === item.id ? "configuration-selected" : ""}`} aria-pressed={configuration === item.id}
                  disabled={Boolean(operation)} onClick={() => { setConfiguration(item.id); setSelectedShares([]); }}>
                  <span className="configuration-code">{item.id}</span><span className="configuration-copy"><strong>{item.name}</strong><small>{item.description}</small><span className="configuration-path">{item.path}</span></span>
                  <span className="configuration-check">{configuration === item.id && <Check size={14} />}</span>
                </button>
              ))}
            </div>
            {configuration === "E" && <div className="threshold-picker">
              <div className="picker-heading"><Layers3 size={15} /><span>THRESHOLD PRESET</span><span className="picker-hint">k-of-n</span></div>
              <div className="threshold-options" role="group" aria-label="Threshold preset">
                {thresholds.map(([k, n]) => <button key={`${k}-${n}`} className={threshold[0] === k && threshold[1] === n ? "threshold-active" : ""} aria-pressed={threshold[0] === k && threshold[1] === n} disabled={Boolean(operation)} onClick={() => { setThreshold([k, n]); setSelectedShares([]); }}>{k}<span> / </span>{n}</button>)}
              </div>
            </div>}
            <div className="config-footer">
              <span><LockKeyhole size={13} /> Key material remains on the backend</span>
              <span>{configuration}{configuration === "E" ? ` · ${threshold[0]} of ${threshold[1]}` : " · 128 x 128"}</span>
            </div>
            <button className="button button-primary encrypt-button" disabled={!state.image.processed || Boolean(operation)} onClick={() => void encrypt()}>
              {operation === "encrypt" ? <><RefreshCw className="spin" size={16} /> Encrypting image…</> : <><Sparkles size={16} /> Encrypt Image <ArrowRight size={16} /></>}
            </button>
          </div>
        </div>
        {error && <div className="error-callout" role="alert"><CircleHelp size={17} /><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError("")}><X size={16} /></button></div>}
      </section>

      <section className="page-shell section-block" id="pipeline">
        <SectionHeading index="03 / PROCESS" title={<>A visible path<br /><em>through the pipeline.</em></>} detail="The selected configuration determines which stages appear. Activity highlights during a backend run; completion reflects the returned API state." />
        <div className="pipeline-panel glass-panel">
          <div className="pipeline-topline"><span><GitBranch size={15} /> CONFIGURATION {configuration}</span><span className="simulation-label"><span className="mini-led" /> Quantum-Inspired / Classical Simulation</span>{operation === "encrypt" && <span className="pipeline-request-state" role="status"><RefreshCw size={13} className="spin" /> Encryption request running</span>}</div>
          <div className="pipeline-nodes" aria-live="polite">
            {stages.map((stage, index) => {
              const complete = activeConfigurationMatches && ["encrypted", "reconstructed"].includes(state.stage) && operation !== "encrypt";
              return <div className={`pipeline-node ${complete ? "pipeline-complete" : ""}`} key={`${configuration}-${stage}`}>
                <div className="node-marker">{complete ? <Check size={14} /> : <span>{String(index + 1).padStart(2, "0")}</span>}</div>
                <span className="node-label">{stage}</span>
                {index < stages.length - 1 && <span className="node-connector" aria-hidden="true" />}
              </div>;
            })}
          </div>
          <p className="pipeline-caption"><Waves size={14} /> Classical simulation of quantum-inspired transformations. No physical quantum hardware is used in the 128 x 128 workflow.</p>
        </div>
      </section>

      <section className="page-shell section-block" id="results">
        <SectionHeading index="04 / OUTPUT" title={<>Image outputs,<br /><em>side by side.</em></>} detail="Panels show images served by the research backend. Empty states remain until that output exists." />
        <div className="result-grid">
          <ResultCard title="ORIGINAL" subtitle="Uploaded source" src={state.image.original} loading={operation === "upload"} />
          <ResultCard title="ENCRYPTED" subtitle={state.encrypted ? `Configuration ${state.label ?? configuration}` : "Awaiting encryption"} src={state.encrypted} loading={operation === "encrypt"} />
          <ResultCard title="RECONSTRUCTED" subtitle={state.reconstructed ? "Ciphertext reconstructed" : "Awaiting reconstruction"} src={state.reconstructed} loading={operation === "reconstruct"} verified={state.stage === "reconstructed" && activeConfigurationMatches && state.threshold_verified === true} />
          <ResultCard title="DECRYPTED" subtitle={state.decrypted ? "Recovered image" : "Awaiting decryption"} src={state.decrypted} loading={operation === "reconstruct"} verified={state.stage === "reconstructed" && activeConfigurationMatches && state.threshold_verified === true} />
        </div>
        {canDecryptDirectly && <div className="direct-reconstruct-row"><span>Configuration {configuration} is ready for decryption.</span><button className="button button-secondary" disabled={Boolean(operation)} onClick={() => void decrypt()}>{operation === "reconstruct" ? <><RefreshCw size={15} className="spin" /> Decrypting…</> : <>Decrypt Image <ArrowRight size={15} /></>}</button></div>}
      </section>

      <section className="page-shell section-block" id="security">
        <SectionHeading index="05 / SECURITY" title={<>Measured properties.<br /><em>No unsupported claims.</em></>} detail="Metrics are returned by src/metrics.py for the active run. They provide evidence about measured properties, not a cryptographic security proof." />
        <div className="metric-category">
          <div className="metric-category-heading"><h3>Security / Statistical</h3><p>NPCR/UACI are ciphertext differential tests.</p></div>
          <div className="metric-grid">
            {metricCards.slice(0, 6).map(([label, value, unit, kind], index) => <article className="metric-card" key={label} style={{ "--metric-order": index } as CSSProperties}>
              <div className="metric-card-head"><span>{label}</span><span className={`metric-kind kind-${kind}`}>{kind}</span></div>
              <strong>{display(value, label === "PSNR" ? 3 : 4)}</strong><small>{unit}</small>
            </article>)}
          </div>
        </div>
        <div className="metric-category">
          <div className="metric-category-heading"><h3>Quality / Reconstruction</h3><p>Quality measures appear after reconstruction completes.</p></div>
          <div className="metric-grid metric-grid-quality">
            {metricCards.slice(6).map(([label, value, unit, kind], index) => <article className="metric-card" key={label} style={{ "--metric-order": index } as CSSProperties}>
              <div className="metric-card-head"><span>{label}</span><span className={`metric-kind kind-${kind}`}>{kind}</span></div>
              <strong>{display(value, label === "PSNR" ? 3 : 4)}</strong><small>{unit}</small>
            </article>)}
          </div>
        </div>
        <p className="evidence-note"><Shield size={15} /> Empirical measurements, not a cryptographic security proof. N/A means the current API did not return that measure.</p>
        <CorrelationTrack label="Horizontal" value={metrics?.correlation_horizontal} />
        <CorrelationTrack label="Vertical" value={metrics?.correlation_vertical} />
        <CorrelationTrack label="Diagonal" value={metrics?.correlation_diagonal} />
      </section>

      <section className={`page-shell section-block sharing-section ${configuration === "E" ? "sharing-emphasized" : ""}`} id="sharing">
        <SectionHeading index="06 / THRESHOLD SHARING" title={<>Distribute access<br /><em>across image shares.</em></>} detail="Threshold controls and reconstruction activate for configuration E. Select at least k shares before requesting reconstruction." />
        {configuration !== "E" ? <div className="sharing-inactive glass-panel"><Layers3 size={20} /><span>Choose configuration E in the Encryption Lab to generate and select threshold shares.</span><a href="#lab">Configure E <ArrowRight size={14} /></a></div> : <div className="sharing-panel glass-panel">
          {!matchingShareSet ? <div className="sharing-empty"><span className="section-icon violet-icon"><Layers3 size={17} /></span><div><strong>{state.label === "E" ? "Threshold selection changed" : "Shares appear after encryption"}</strong><p>{state.label === "E" ? "Encrypt again with the selected preset to generate a matching share set." : "Select a supported k-of-n preset, then encrypt an image to generate the shares."}</p></div><span className="threshold-summary">{threshold[0]} of {threshold[1]}</span></div> : <>
            <div className="share-summary"><div><span className="micro-label">REQUIRED</span><strong>{requiredShares} <small>shares</small></strong></div><div><span className="micro-label">TOTAL AVAILABLE</span><strong>{state.shares.length} <small>shares</small></strong></div><div><span className="micro-label">SELECTED</span><strong>{selectedShares.length}<small> / {threshold[1]}</small></strong></div><div className="share-readiness"><span className={`readiness-led ${selectedShares.length >= requiredShares ? "ready" : ""}`} />{selectedShares.length >= requiredShares ? "READY TO RECONSTRUCT" : `${requiredShares - selectedShares.length} MORE REQUIRED`}</div></div>
            <div className="shares-grid" role="group" aria-label="Select image shares">
              {state.shares.map((share) => <button key={share.index} className={`share-card ${selectedShares.includes(share.index) ? "share-selected" : ""}`} aria-pressed={selectedShares.includes(share.index)} onClick={() => setSelectedShares((current) => current.includes(share.index) ? current.filter((index) => index !== share.index) : [...current, share.index])}>
                <span className="share-thumb"><Image src={share.url} alt={`Share ${share.index} preview`} fill sizes="120px" unoptimized style={{ objectFit: "cover" }} /></span><span className="share-card-text"><strong>SHARE {String(share.index).padStart(2, "0")}</strong><small>{selectedShares.includes(share.index) ? "SELECTED" : "AVAILABLE"}</small></span><span className="share-check">{selectedShares.includes(share.index) && <Check size={15} />}</span>
              </button>)}
            </div>
            <p className="share-selection-note">Any distinct set of {requiredShares} shares can satisfy this threshold.</p>
            <div className="reconstruction-footer"><p>Threshold {threshold[0]}-of-{threshold[1]} · GF(2^8) interpolation · XOR field addition</p><button className="button button-primary" disabled={selectedShares.length < requiredShares || Boolean(operation)} onClick={() => void decrypt()}>{operation === "reconstruct" ? <><RefreshCw size={15} className="spin" /> Reconstructing…</> : <>Reconstruct and decrypt <ArrowRight size={15} /></>}</button></div>
            {state.threshold_verified && <div className="success-callout"><Check size={16} /><span>Threshold satisfied</span><span>Reconstruction successful</span></div>}
          </>}
        </div>}
      </section>

      <section className="page-shell section-block" id="performance">
        <SectionHeading index="07 / RESOURCES" title={<>Performance &amp;<br /><em>storage profile.</em></>} detail="Operation timings and share storage measurements come from the active backend response. Unreported values remain N/A." />
        <div className="performance-group"><h3>Performance</h3><div className="performance-grid performance-grid-four">
          <PerformanceCard icon={<Gauge size={16} />} label="Encryption time" value={display(configuration === "E" ? metrics?.threshold_pipeline_time_ms : metrics?.encryption_time_ms, 2)} unit="ms" />
          <PerformanceCard icon={<RefreshCw size={16} />} label="Decryption time" value={display(metrics?.decryption_time_ms, 2)} unit="ms" />
          <PerformanceCard icon={<Layers3 size={16} />} label="Share generation" value={display(metrics?.share_generation_time_ms, 2)} unit="ms" />
          <PerformanceCard icon={<GitBranch size={16} />} label="Reconstruction" value={display(configuration === "E" ? metrics?.reconstruction_decryption_time_ms : metrics?.reconstruction_time_ms, 2)} unit="ms" />
        </div></div>
        <div className="performance-group"><h3>Storage</h3><div className="performance-grid performance-grid-storage">
          <PerformanceCard icon={<Database size={16} />} label="Bytes / share" value={numeric(metrics?.bytes_per_share) === null ? "N/A" : `${(Number(metrics?.bytes_per_share) / 1024).toFixed(1)} KB`} unit="" />
          <PerformanceCard icon={<Network size={16} />} label="Storage ratio" value={display(metrics?.storage_overhead_ratio, 2)} unit="x" />
        </div></div>
      </section>

      <section className="page-shell section-block" id="experiments">
        <SectionHeading index="08 / EXPERIMENTS" title={<>Recorded results,<br /><em>from the research run.</em></>} detail="Load the existing experiment result endpoint. Values below are read from its response and are never populated with example numbers." />
        <div className="experiment-panel glass-panel">
          <div className="experiment-toolbar">
            <div><span className="section-icon"><FlaskConical size={16} /></span><span>{resultsLoaded ? results.length + " records returned" : "Experiment result archive"}</span></div>
            <button className="button button-secondary" onClick={() => void loadResults()} disabled={Boolean(operation) || resultsLoading}>
              {resultsLoading ? <><RefreshCw size={14} className="spin" /> Loading results...</> : resultsLoaded ? <><RefreshCw size={14} /> Refresh results</> : <>Load experiment results <ArrowRight size={14} /></>}
            </button>
          </div>
          {resultsError && <div className="error-callout results-error" role="alert">{resultsError}</div>}
          {!resultsLoaded ? <div className="table-empty"><Database size={20} /><span>Load the result archive to inspect recorded configurations and metrics.</span></div> : results.length === 0 ? <div className="table-empty"><Database size={20} /><span>The endpoint returned no experiment rows.</span></div> : <>
            <div className="experiment-summary" aria-label="Experiment result summary">
              <div><span>Returned rows</span><strong>{results.length}</strong></div>
              <div><span>Successful</span><strong>{successfulResults}</strong></div>
              <div><span>Failed</span><strong>{failedResults}</strong></div>
              <div><span>Configurations</span><strong>{new Set(results.map((row) => String(row.configuration ?? "N/A"))).size} / 5</strong></div>
            </div>
            <div className="table-scroll">
              <table>
                <caption className="visually-hidden">Recorded image-encryption experiment results</caption>
                <thead><tr><th>STATUS</th><th>CONFIG</th><th>THRESHOLD</th><th>IMAGE</th><th>ENTROPY</th><th>H CORR</th><th>V CORR</th><th>D CORR</th><th>NPCR</th><th>UACI</th><th>ENCRYPT MS</th></tr></thead>
                <tbody>{visibleResults.map((row, index) => {
                  const parameters = row.configuration_parameters as { threshold_k?: unknown; threshold_n?: unknown } | undefined;
                  const thresholdLabel = row.configuration === "E" && parameters?.threshold_k != null && parameters.threshold_n != null
                    ? String(parameters.threshold_k) + "-of-" + String(parameters.threshold_n)
                    : "N/A";
                  const status = String(row.status ?? "N/A");
                  return <tr key={String(row.experiment_id ?? index)}>
                    <td><span className={status.toLowerCase() === "success" ? "experiment-status success" : "experiment-status"}>{status}</span></td>
                    <td><span className="table-config">{String(row.configuration ?? "N/A")}</span></td>
                    <td>{thresholdLabel}</td><td>{String(row.image_name ?? "N/A")}</td>
                    <td>{display(row.entropy)}</td><td>{display(row.correlation_horizontal)}</td><td>{display(row.correlation_vertical)}</td>
                    <td>{display(row.correlation_diagonal)}</td><td>{display(row.npcr)}</td><td>{display(row.uaci)}</td><td>{display(row.encryption_time_ms, 2)}</td>
                  </tr>;
                })}</tbody>
              </table>
            </div>
            {results.length > 12 && <div className="table-footer">
              <span>Showing {visibleResults.length} of {results.length} result rows</span>
              <button className="button button-quiet" onClick={() => setShowAllResults((show) => !show)}>{showAllResults ? "Show fewer" : "Show all " + results.length + " results"}</button>
            </div>}
          </> }
        </div>
      </section>

      <section className="page-shell section-block" id="methodology">
        <SectionHeading index="09 / METHODOLOGY" title={<>Five stages.<br /><em>One research workflow.</em></>} detail="The large-image workflow combines classical algorithms with reversible transformations inspired by quantum operations." />
        <div className="method-grid">
          <MethodCard number="01" icon={<Waves size={17} />} title="LOGISTIC MAP" body="Chaotic key generation" />
          <MethodCard number="02" icon={<Network size={17} />} title="ARNOLD CAT MAP" body="Position scrambling" />
          <MethodCard number="03" icon={<Atom size={17} />} title="QUANTUM-INSPIRED TRANSFORM" body="Reversible bit-mixing; CNOT-inspired controlled XOR; X-inspired bit flip; Z-inspired reversible byte rotation" />
          <MethodCard number="04" icon={<LockKeyhole size={17} />} title="XOR DIFFUSION" body="Pixel-wise diffusion" />
          <MethodCard number="05" icon={<Layers3 size={17} />} title="GF(2^8) THRESHOLD SHARING" body="Threshold reconstruction using finite-field arithmetic" />
        </div>
        <div className="method-detail"><span className="detail-rule" /><p><strong>Threshold method</strong> GF(2^8)-based threshold image secret sharing with XOR field addition</p></div>
        <div className="research-disclaimer"><Shield size={17} /><p><strong>Research note:</strong> These operations are classical reversible analogues inspired by selected quantum-gate transformations; they are not physical quantum gates in the 128{"\u00d7"}128 pipeline. The workflow does not execute on quantum hardware and is not post-quantum cryptography. Metrics are empirical measures, not security proofs.</p></div>
      </section>

      <footer className="page-shell footer"><a className="brand" href="#home"><span className="brand-mark"><Sparkles size={15} /></span><span>Q-CRYPT</span></a><span>RESEARCH INTERFACE / CLASSICAL SIMULATION</span><a href="#home">Back to top <ArrowDown size={13} className="arrow-up" /></a></footer>
    </main>
  );
}

function SectionHeading({ index, title, detail }: { index: string; title: ReactNode; detail: string }) {
  return <div className="section-heading"><div><span className="eyebrow"><span className="eyebrow-line" />{index}</span><h2>{title}</h2></div><p>{detail}</p></div>;
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div className="fact"><span>{label}</span><strong>{value}</strong></div>;
}

function ResultCard({ title, subtitle, src, loading = false, verified = false }: { title: string; subtitle: string; src: string | null; loading?: boolean; verified?: boolean }) {
  const stateLabel = loading ? "PROCESSING" : verified ? "VERIFIED" : src ? "AVAILABLE" : "PENDING";
  return <article className="result-card">
    <div className="result-accent" />
    <div className="result-card-heading"><span>{title}</span><span className={verified ? "result-state result-state-ready" : loading ? "result-state result-state-running" : "result-state"} aria-live="polite">{stateLabel}</span></div>
    <div className="result-image">{src ? <Image src={src} alt={`${title.toLowerCase()} image`} fill sizes="(max-width: 720px) 90vw, 45vw" unoptimized style={{ objectFit: "contain" }} /> : <div className="result-placeholder">{loading ? <><RefreshCw size={20} className="spin" /><span>Processing {title.toLowerCase()}…</span></> : <><FileImage size={23} /><span>{subtitle}</span></>}</div>}</div>
    <div className="result-caption"><span>{subtitle}</span>{src && <a href={src} download aria-label={`Download ${title.toLowerCase()} image`}><ArrowDown size={14} /></a>}</div>
  </article>;
}

function CorrelationTrack({ label, value }: { label: string; value: unknown }) {
  const number = numeric(value);
  const position = number === null ? null : `${Math.max(0, Math.min(100, (number + 1) * 50))}%`;
  return <div className="correlation-row"><span>{label}</span><div className="correlation-scale"><i className="scale-zero" />{position && <i className="scale-value" style={{ left: position }} />}</div><strong>{display(value)}</strong></div>;
}

function PerformanceCard({ icon, label, value, unit }: { icon: ReactNode; label: string; value: string; unit: string }) {
  return <article className="performance-card"><span className="performance-icon">{icon}</span><span className="performance-label">{label}</span><strong>{value}<small>{unit}</small></strong></article>;
}

function MethodCard({ number, icon, title, body }: { number: string; icon: ReactNode; title: string; body: string }) {
  return <article className="method-card"><div className="method-card-top"><span>{number}</span>{icon}</div><h3>{title}</h3><p>{body}</p><span className="method-card-line" /></article>;
}
