import type { Metadata } from "next";
import { Providers } from "@/components/providers";
import "./globals.css";
import { AuthGate } from "@/components/auth-gate";
export const metadata: Metadata = {
  title: "PolyaBrain",
  description:
    "Understand problems, acquire knowledge, and work toward verified outcomes with inspectable evidence.",
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
