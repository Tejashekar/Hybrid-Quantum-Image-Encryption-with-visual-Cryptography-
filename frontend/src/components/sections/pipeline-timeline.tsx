"use client";
import React from "react";
import { Timeline } from "@/components/ui/timeline";
import {
  Upload,
  Lock,
  SplitSquareVertical,
  Merge,
  BarChart3,
  Shield,
  KeyRound,
  Eye,
} from "lucide-react";

export default function PipelineTimeline() {
  const data = [
    {
      title: "Upload",
      content: (
        <div>
          <p className="text-neutral-300 text-sm md:text-base font-normal mb-6">
            Start by uploading any image. It is automatically resized to
            128&times;128 and converted to grayscale — the standard input for
            the quantum-inspired encryption pipeline.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <FeatureCard
              icon={Upload}
              title="Drag & Drop"
              desc="Drop a PNG, JPG, BMP or TIFF file."
            />
            <FeatureCard
              icon={Eye}
              title="Live Preview"
              desc="See original and preprocessed side-by-side."
            />
          </div>
        </div>
      ),
    },
    {
      title: "Encrypt",
      content: (
        <div>
          <p className="text-neutral-300 text-sm md:text-base font-normal mb-6">
            A random 128&times;128 key is generated and XOR-encrypted with the
            preprocessed image. The result is a noise-like ciphertext that
            reveals nothing about the original.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <FeatureCard
              icon={KeyRound}
              title="Random Key"
              desc="Cryptographic-strength random byte matrix."
            />
            <FeatureCard
              icon={Lock}
              title="XOR Cipher"
              desc="Bit-level encryption — fast and reversible."
            />
          </div>
        </div>
      ),
    },
    {
      title: "Split",
      content: (
        <div>
          <p className="text-neutral-300 text-sm md:text-base font-normal mb-6">
            The encrypted image is split into two shares using visual
            cryptography. Each share alone looks like random noise; only
            combining both reveals the ciphertext.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <FeatureCard
              icon={SplitSquareVertical}
              title="Share Generation"
              desc="Two XOR-complementary share images."
            />
            <FeatureCard
              icon={Shield}
              title="Zero Leakage"
              desc="Individual share reveals zero information."
            />
          </div>
        </div>
      ),
    },
    {
      title: "Reconstruct",
      content: (
        <div>
          <p className="text-neutral-300 text-sm md:text-base font-normal mb-6">
            XOR-merge the two shares back together to reconstruct the
            ciphertext, then decrypt with the session key to recover the
            original image perfectly.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <FeatureCard
              icon={Merge}
              title="Share Fusion"
              desc="XOR-combine both shares to reconstruct."
            />
            <FeatureCard
              icon={Eye}
              title="Lossless Recovery"
              desc="Decrypted image matches the original exactly."
            />
          </div>
        </div>
      ),
    },
    {
      title: "Metrics",
      content: (
        <div>
          <p className="text-neutral-300 text-sm md:text-base font-normal mb-6">
            Evaluate the quality of encryption with industry-standard measures:
            entropy, pixel correlation, NPCR, UACI, and PSNR.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <MetricBadge label="Entropy" value="~7.99" />
            <MetricBadge label="Correlation" value="~0.00" />
            <MetricBadge label="NPCR" value="~99.6%" />
            <MetricBadge label="UACI" value="~33.5%" />
            <MetricBadge label="PSNR" value="∞ dB" />
            <FeatureCard
              icon={BarChart3}
              title="Dashboard"
              desc="All metrics in one view."
            />
          </div>
        </div>
      ),
    },
  ];

  return (
    <section className="w-full">
      <div className="max-w-7xl mx-auto py-20 px-4 md:px-8 lg:px-10">
        <h2 className="text-lg md:text-4xl mb-4 text-white max-w-4xl font-bold">
          How the Pipeline Works
        </h2>
        <p className="text-neutral-400 text-sm md:text-base max-w-sm">
          A step-by-step walkthrough of the quantum-inspired image encryption
          and visual cryptography pipeline.
        </p>
      </div>
      <Timeline data={data} />
    </section>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  desc,
}: {
  icon: React.ElementType;
  title: string;
  desc: string;
}) {
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 shadow-[0_0_24px_rgba(34,42,53,0.06),_0_1px_1px_rgba(0,0,0,0.05),_0_0_0_1px_rgba(34,42,53,0.04),_0_0_4px_rgba(34,42,53,0.08),_0_16px_68px_rgba(47,48,55,0.05),_0_1px_0_rgba(255,255,255,0.1)_inset]">
      <Icon className="h-6 w-6 text-purple-400 mb-2" />
      <h4 className="text-sm font-semibold text-neutral-200">{title}</h4>
      <p className="text-xs text-neutral-500 mt-1">{desc}</p>
    </div>
  );
}

function MetricBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 text-center shadow-[0_0_24px_rgba(34,42,53,0.06),_0_1px_1px_rgba(0,0,0,0.05),_0_0_0_1px_rgba(34,42,53,0.04),_0_0_4px_rgba(34,42,53,0.08),_0_16px_68px_rgba(47,48,55,0.05),_0_1px_0_rgba(255,255,255,0.1)_inset]">
      <p className="text-xs text-neutral-500 uppercase tracking-wider">{label}</p>
      <p className="text-lg font-bold text-emerald-400 mt-1">{value}</p>
    </div>
  );
}
