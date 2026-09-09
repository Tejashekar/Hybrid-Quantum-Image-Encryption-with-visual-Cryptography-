"use client";

import HeroSection from "@/components/sections/hero-section";
import PipelineTimeline from "@/components/sections/pipeline-timeline";
import UploadSection from "@/components/sections/upload-section";
import EncryptSection from "@/components/sections/encrypt-section";
import ReconstructSection from "@/components/sections/reconstruct-section";
import MetricsSection from "@/components/sections/metrics-section";
import { PipelineProvider } from "@/lib/pipeline-context";
import { Shield } from "lucide-react";

export default function Home() {
  return (
    <PipelineProvider>
      <div className="min-h-screen bg-neutral-950 text-white">
        {/* Floating nav */}
        <nav className="fixed top-4 left-1/2 -translate-x-1/2 z-50 backdrop-blur-lg bg-neutral-900/70 border border-neutral-800 rounded-full px-6 py-2.5 flex items-center gap-6 shadow-2xl">
          <Shield className="h-5 w-5 text-purple-400" />
          <a href="#hero" className="text-xs text-neutral-400 hover:text-white transition-colors">
            Home
          </a>
          <a href="#pipeline" className="text-xs text-neutral-400 hover:text-white transition-colors">
            Pipeline
          </a>
          <a href="#upload" className="text-xs text-neutral-400 hover:text-white transition-colors">
            Upload
          </a>
          <a href="#encrypt" className="text-xs text-neutral-400 hover:text-white transition-colors">
            Encrypt
          </a>
          <a href="#reconstruct" className="text-xs text-neutral-400 hover:text-white transition-colors">
            Reconstruct
          </a>
          <a href="#metrics" className="text-xs text-neutral-400 hover:text-white transition-colors">
            Metrics
          </a>
        </nav>

        {/* Hero with container scroll animation */}
        <div id="hero">
          <HeroSection />
        </div>

        {/* Pipeline timeline */}
        <div id="pipeline">
          <PipelineTimeline />
        </div>

        {/* Divider */}
        <div className="max-w-5xl mx-auto px-4">
          <hr className="border-neutral-800" />
        </div>

        {/* Interactive pipeline steps */}
        <div id="upload">
          <UploadSection />
        </div>

        <div className="max-w-5xl mx-auto px-4">
          <hr className="border-neutral-800" />
        </div>

        <div id="encrypt">
          <EncryptSection />
        </div>

        <div className="max-w-5xl mx-auto px-4">
          <hr className="border-neutral-800" />
        </div>

        <div id="reconstruct">
          <ReconstructSection />
        </div>

        <div className="max-w-5xl mx-auto px-4">
          <hr className="border-neutral-800" />
        </div>

        <div id="metrics">
          <MetricsSection />
        </div>

        {/* Footer */}
        <footer className="border-t border-neutral-800 mt-20 py-10 text-center text-neutral-600 text-xs">
          Quantum Image Encryption + Visual Cryptography &mdash; Built with Next.js, shadcn/ui &amp; Flask
        </footer>
      </div>
    </PipelineProvider>
  );
}
