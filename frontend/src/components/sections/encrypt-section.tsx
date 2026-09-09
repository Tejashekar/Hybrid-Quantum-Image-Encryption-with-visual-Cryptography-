"use client";
import React, { useState } from "react";
import { motion } from "framer-motion";
import { Lock, Download, Loader2, ImageIcon } from "lucide-react";
import { usePipeline } from "@/lib/pipeline-context";
import { runEncrypt, outputUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function EncryptSection() {
  const { state, setState } = usePipeline();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEncrypt = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await runEncrypt();
      setState(res.state);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Encryption failed");
    } finally {
      setLoading(false);
    }
  };

  const hasProcessed = !!state.processed;
  const hasEncrypted = !!state.encrypted;

  return (
    <section className="max-w-5xl mx-auto px-4 py-20">
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        viewport={{ once: true }}
      >
        <h2 className="text-3xl md:text-5xl font-bold mb-2 bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
          Step 2 &mdash; Encrypt &amp; Split
        </h2>
        <p className="text-neutral-400 mb-8 max-w-lg">
          XOR-encrypt the preprocessed image with a random key, then generate
          two visual cryptography shares.
        </p>

        <Button
          onClick={handleEncrypt}
          disabled={loading || !hasProcessed}
          className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-xl flex items-center gap-2 text-base disabled:opacity-40"
        >
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Lock className="h-5 w-5" />
          )}
          {loading ? "Encrypting…" : "Run Encryption + Share Generation"}
        </Button>

        {error && <p className="mt-3 text-red-400 text-sm">{error}</p>}

        {hasEncrypted && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-10">
            <ImageCard title="Encrypted" filename={state.encrypted!} />
            <ImageCard title="Share 1" filename={state.share1!} />
            <ImageCard title="Share 2" filename={state.share2!} />
          </div>
        )}
      </motion.div>
    </section>
  );
}

function ImageCard({ title, filename }: { title: string; filename: string }) {
  const src = outputUrl(filename);
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
      <a
        href={src}
        download
        className="mt-3 inline-flex items-center gap-1.5 text-xs text-purple-400 hover:text-purple-300 transition-colors"
      >
        <Download className="h-3.5 w-3.5" /> Download
      </a>
    </div>
  );
}
