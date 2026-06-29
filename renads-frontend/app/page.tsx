import type { Metadata } from "next";
import { Lexend, Source_Sans_3 } from "next/font/google";

import { Landing } from "@/components/landing/landing";

export const metadata: Metadata = {
  title: "RENADS — Registro Nacional de Articulación Docencia-Servicio en Salud",
  description:
    "Plataforma del MINSA para gestionar convenios, internados y actividades docente-asistenciales con trazabilidad total.",
};

// Tipografía del MASTER (design-system/renadsweb): Lexend (títulos) + Source Sans 3 (cuerpo).
const lexend = Lexend({
  subsets: ["latin"],
  variable: "--font-lexend",
  weight: ["300", "400", "500", "600", "700"],
});
const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-source",
  weight: ["300", "400", "500", "600", "700"],
});

/**
 * Landing pública (raíz). Paleta del MASTER vía `.landing-theme` (claro/oscuro en globals.css)
 * + efectos (glass, partículas, framer-motion). El dark mode lo controla next-themes (Providers).
 */
export default function Page() {
  return (
    <div className={`landing-theme ${lexend.variable} ${sourceSans.variable}`}>
      <Landing />
    </div>
  );
}
