import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Caveat } from "next/font/google";
import { LandingPage } from "@/features/landing/landing-page";

const landingFont = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-landing",
});
const handwriting = Caveat({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-handwriting",
});

export const metadata: Metadata = {
  title: "ASGARD | Planeación pedagógica para instructores SENA",
  description:
    "ASGARD acompaña a los instructores del SENA en la construcción de programas, proyectos y planeaciones pedagógicas mediante un flujo guiado, estructurado y trazable.",
};

export default function HomePage(): React.JSX.Element {
  return (
    <LandingPage
      className={`${landingFont.variable} ${handwriting.variable}`}
    />
  );
}
