import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Q-CRYPT | Quantum-Inspired Image Encryption",
  description:
    "A research framework for classical simulation of quantum-inspired image encryption and GF(2^8)-based threshold image secret sharing.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
