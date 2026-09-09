"use client";
import React, { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { Upload, ImageIcon, CheckCircle2, Loader2 } from "lucide-react";
import { usePipeline } from "@/lib/pipeline-context";
import { uploadImage, inputUrl, outputUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function UploadSection() {
  const { state, setState } = usePipeline();
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setLoading(true);
      setError(null);
      try {
        const res = await uploadImage(file);
        setState(res.state);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setLoading(false);
      }
    },
    [setState],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const onSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  return (
    <section className="max-w-5xl mx-auto px-4 py-20">
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        viewport={{ once: true }}
      >
        <h2 className="text-3xl md:text-5xl font-bold mb-2 bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
          Step 1 &mdash; Upload &amp; Preprocess
        </h2>
        <p className="text-neutral-400 mb-8 max-w-lg">
          Drop an image below. It will be converted to 128&times;128 grayscale
          for the encryption pipeline.
        </p>

        {/* Drop zone */}
        <div
          role="button"
          tabIndex={0}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={`relative flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed p-10 transition-colors cursor-pointer
            ${dragging ? "border-cyan-400 bg-cyan-400/10" : "border-neutral-700 bg-neutral-900/50 hover:border-neutral-500"}`}
        >
          {loading ? (
            <Loader2 className="h-10 w-10 animate-spin text-cyan-400" />
          ) : state.processed ? (
            <CheckCircle2 className="h-10 w-10 text-emerald-400" />
          ) : (
            <Upload className="h-10 w-10 text-neutral-500" />
          )}
          <p className="text-neutral-400 text-sm">
            {loading
              ? "Processing…"
              : "Drag & drop an image here, or click to browse"}
          </p>
          <input
            type="file"
            accept=".png,.jpg,.jpeg,.bmp,.tif,.tiff"
            onChange={onSelect}
            title="Upload image"
            className="absolute inset-0 opacity-0 cursor-pointer"
          />
        </div>

        {error && (
          <p className="mt-3 text-red-400 text-sm">{error}</p>
        )}

        {/* Previews */}
        {(state.original || state.processed) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-10">
            {state.original && (
              <PreviewCard title="Original" src={inputUrl(state.original)} />
            )}
            {state.processed && (
              <PreviewCard title="Preprocessed (128×128)" src={outputUrl(state.processed)} />
            )}
          </div>
        )}
      </motion.div>
    </section>
  );
}

function PreviewCard({ title, src }: { title: string; src: string }) {
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
