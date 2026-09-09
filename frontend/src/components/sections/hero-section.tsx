"use client";
import React from "react";
import { ContainerScroll } from "@/components/ui/container-scroll-animation";
import { Shield, Lock, SplitSquareVertical, BarChart3 } from "lucide-react";

export default function HeroSection() {
  return (
    <div className="flex flex-col overflow-hidden">
      <ContainerScroll
        titleComponent={
          <>
            <h1 className="text-4xl font-semibold text-white">
              Quantum-Inspired <br />
              <span className="text-4xl md:text-[6rem] font-bold mt-1 leading-none bg-gradient-to-r from-purple-400 via-blue-400 to-cyan-400 bg-clip-text text-transparent">
                Image Encryption
              </span>
            </h1>
            <p className="mt-4 text-neutral-400 text-lg max-w-2xl mx-auto">
              Secure your images with XOR encryption, split them into
              cryptographic shares using visual cryptography, and reconstruct
              them only when both halves reunite.
            </p>
          </>
        }
      >
        {/* Dashboard preview inside the 3D card */}
        <div className="h-full w-full bg-gradient-to-br from-neutral-900 via-neutral-800 to-neutral-900 p-6 md:p-10 flex flex-col gap-6 overflow-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { icon: Shield, label: "Upload & Preprocess", color: "text-cyan-400" },
              { icon: Lock, label: "Encrypt Image", color: "text-purple-400" },
              { icon: SplitSquareVertical, label: "Visual Crypto Shares", color: "text-blue-400" },
              { icon: BarChart3, label: "Security Metrics", color: "text-emerald-400" },
            ].map((item, i) => (
              <div
                key={i}
                className="flex flex-col items-center gap-2 rounded-xl border border-neutral-700 bg-neutral-800/60 p-4 text-center"
              >
                <item.icon className={`h-8 w-8 ${item.color}`} />
                <span className="text-xs md:text-sm text-neutral-300">
                  {item.label}
                </span>
              </div>
            ))}
          </div>

          <div className="flex-1 rounded-xl border border-neutral-700 bg-neutral-800/40 flex items-center justify-center">
            <p className="text-neutral-500 text-sm">
              Scroll down to begin the pipeline &darr;
            </p>
          </div>
        </div>
      </ContainerScroll>
    </div>
  );
}
