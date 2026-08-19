import type { Metadata } from "next";
import { Fraunces, Source_Sans_3 } from "next/font/google";

import { AppToaster } from "@/components/feedback/app-toaster";
import { ConfirmProvider } from "@/components/feedback/confirm-context";

import "./globals.css";

const displayFont = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["500", "600", "700"],
});

const bodyFont = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-sans",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "ASGARD | Dashboard maestro SENA",
  description:
    "Panel maestro para gobernar programa, proyecto y planeacion pedagogica en la Fase 1 de guias de aprendizaje SENA.",
};

type RootLayoutProps = Readonly<{
  children: React.ReactNode;
}>;

export default function RootLayout({
  children,
}: RootLayoutProps): React.JSX.Element {
  return (
    <html lang="es">
      <body className={`${displayFont.variable} ${bodyFont.variable}`}>
        <ConfirmProvider>
          {children}
          <AppToaster />
        </ConfirmProvider>
      </body>
    </html>
  );
}
