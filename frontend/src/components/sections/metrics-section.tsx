"use client";
import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { RefreshCw, Loader2, ImageIcon } from "lucide-react";
import { usePipeline } from "@/lib/pipeline-context";
import { outputUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function MetricsSection() {
  const { state, metrics, refreshMetrics } = usePipeline();
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    await refreshMetrics();
    setLoading(false);
  };

  // Auto-fetch when decrypted first appears
  useEffect(() => {
    if (state.decrypted && !metrics) {
      load();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.decrypted]);

  return (
    <section className="max-w-5xl mx-auto px-4 py-20">
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        viewport={{ once: true }}
      >
        <h2 className="text-3xl md:text-5xl font-bold mb-2 bg-gradient-to-r from-emerald-400 to-yellow-400 bg-clip-text text-transparent">
          Step 4 &mdash; Security Metrics
        </h2>
        <p className="text-neutral-400 mb-8 max-w-lg">
          Evaluate encryption quality with entropy, correlation, NPCR, UACI and
          PSNR measurements.
        </p>

        <Button
          onClick={load}
          disabled={loading}
          className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-xl flex items-center gap-2 text-base"
        >
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <RefreshCw className="h-5 w-5" />
          )}
          {loading ? "Calculating…" : "Load Metrics"}
        </Button>

        {metrics && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-10">
              <MetricCard label="Entropy" value={metrics.entropy_encrypted} ideal="~7.99" color="from-purple-500 to-pink-500" />
              <MetricCard label="Correlation" value={metrics.correlation_encrypted} ideal="~0" color="from-blue-500 to-cyan-500" />
              <MetricCard label="NPCR %" value={metrics.npcr} ideal="~99.6" color="from-emerald-500 to-green-500" />
              <MetricCard label="UACI %" value={metrics.uaci} ideal="~33.5" color="from-yellow-500 to-orange-500" />
              <MetricCard
                label="PSNR (dB)"
                value={metrics.psnr_original_vs_decrypted}
                ideal="∞ if lossless"
                color="from-red-500 to-pink-500"
              />
            </div>

            {/* Image comparison */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-10">
              {state.processed && (
                <ImgCard title="Preprocessed" src={outputUrl(state.processed)} />
              )}
              {state.encrypted && (
                <ImgCard title="Encrypted" src={outputUrl(state.encrypted)} />
              )}
              {state.decrypted && (
                <ImgCard title="Decrypted" src={outputUrl(state.decrypted)} />
              )}
            </div>
          </>
        )}

        {!metrics && !loading && (
          <p className="mt-6 text-neutral-500 text-sm">
            Complete all previous steps first, then press &ldquo;Load Metrics&rdquo;.
          </p>
        )}
      </motion.div>
    </section>
  );
}

function MetricCard({
  label,
  value,
  ideal,
  color,
}: {
  label: string;
  value: number | string;
  ideal: string;
  color: string;
}) {
  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4 text-center">
      <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">
        {label}
      </p>
      <p
        className={`text-2xl font-bold bg-gradient-to-r ${color} bg-clip-text text-transparent`}
      >
        {typeof value === "number" ? value.toFixed(4) : value}
      </p>
      <p className="text-[0.65rem] text-neutral-600 mt-1">Ideal: {ideal}</p>
    </div>
  );
}

function ImgCard({ title, src }: { title: string; src: string }) {
  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4">
      <h4 className="text-sm font-semibold text-neutral-300 mb-3 flex items-center gap-2">
        <ImageIcon className="h-4 w-4" /> {title}
      </h4>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={title}
        className="w-full rounded-lg border border-neutral-800"
        style={{ imageRendering: "pixelated" }}
      />
    </div>
  );
}
