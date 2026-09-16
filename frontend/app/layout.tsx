import type { Metadata } from "next";
import { Providers } from "@/components/providers";
import "./globals.css";
import { AuthGate } from "@/components/auth-gate";
export const metadata: Metadata = {
  title: "PolyaBrain · Investigator",
  description:
    "Investigate difficult problems with inspectable evidence, explicit uncertainty, and checked outcomes.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <AuthGate>{children}</AuthGate>
        </Providers>
      </body>
    </html>
  );
}
