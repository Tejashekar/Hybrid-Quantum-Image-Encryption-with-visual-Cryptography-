"use client";
import React, { useState, useRef } from "react";
import { motion } from "framer-motion";
import { Merge, Loader2, ImageIcon, Upload } from "lucide-react";
import { usePipeline } from "@/lib/pipeline-context";
import { runReconstruct, outputUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function ReconstructSection() {
  const { state, setState } = usePipeline();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const share1Ref = useRef<HTMLInputElement>(null);
  const share2Ref = useRef<HTMLInputElement>(null);

  const handleReconstruct = async () => {
    setLoading(true);
    setError(null);
    try {
      const s1 = share1Ref.current?.files?.[0];
      const s2 = share2Ref.current?.files?.[0];
      const res = await runReconstruct(s1, s2);
      setState(res.state);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Reconstruction failed");
    } finally {
      setLoading(false);
    }
  };

  const canRun = !!(state.share1 && state.share2);

  return (
    <section className="max-w-5xl mx-auto px-4 py-20">
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        viewport={{ once: true }}
      >
        <h2 className="text-3xl md:text-5xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
          Step 3 &mdash; Reconstruct &amp; Decrypt
        </h2>
        <p className="text-neutral-400 mb-8 max-w-lg">
          Combine both shares to reconstruct the encrypted image, then XOR-decrypt
          with the session key. Optionally upload external shares instead.
        </p>

        {/* Optional upload slots */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <label className="flex items-center gap-3 rounded-xl border border-neutral-800 bg-neutral-900/60 p-4 cursor-pointer hover:border-neutral-600 transition-colors">
            <Upload className="h-5 w-5 text-neutral-500" />
            <span className="text-sm text-neutral-400">Share 1 (optional)</span>
            <input
              ref={share1Ref}
              type="file"
              accept=".png,.jpg,.jpeg,.bmp,.tif,.tiff"
              className="hidden"
            />
          </label>
          <label className="flex items-center gap-3 rounded-xl border border-neutral-800 bg-neutral-900/60 p-4 cursor-pointer hover:border-neutral-600 transition-colors">
            <Upload className="h-5 w-5 text-neutral-500" />
            <span className="text-sm text-neutral-400">Share 2 (optional)</span>
            <input
              ref={share2Ref}
              type="file"
              accept=".png,.jpg,.jpeg,.bmp,.tif,.tiff"
              className="hidden"
            />
          </label>
        </div>

        <Button
          onClick={handleReconstruct}
          disabled={loading || !canRun}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl flex items-center gap-2 text-base disabled:opacity-40"
        >
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Merge className="h-5 w-5" />
          )}
          {loading ? "Reconstructing…" : "Reconstruct & Decrypt"}
        </Button>

        {error && <p className="mt-3 text-red-400 text-sm">{error}</p>}

        {(state.reconstructed || state.decrypted) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-10">
            {state.reconstructed && (
              <Card title="Reconstructed" src={outputUrl(state.reconstructed)} />
            )}
            {state.decrypted && (
              <Card title="Decrypted" src={outputUrl(state.decrypted)} />
            )}
          </div>
        )}
      </motion.div>
    </section>
  );
}

function Card({ title, src }: { title: string; src: string }) {
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
