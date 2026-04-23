import type { Metadata } from "next";

import { AppProviders } from "@/lib/providers/app-providers";

import "./globals.css";

export const metadata: Metadata = {
  title: "SENA Guia Aprendizaje",
  description:
    "Base tecnica de la Fase 1 para la construccion de guias de aprendizaje SENA.",
};

type RootLayoutProps = Readonly<{
  children: React.ReactNode;
}>;

export default function RootLayout({
  children,
}: RootLayoutProps): React.JSX.Element {
  return (
    <html lang="es">
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
