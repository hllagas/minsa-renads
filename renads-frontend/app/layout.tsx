import type { Metadata } from "next";
import { Lexend, Source_Sans_3, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

// Tipografía del MASTER (design-system/renadsweb): Lexend (títulos) + Source Sans 3 (cuerpo).
const sourceSans = Source_Sans_3({
  variable: "--font-sans",
  subsets: ["latin"],
});

const lexend = Lexend({
  variable: "--font-lexend",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RENADS",
  description: "Registro Nacional de Articulación Docencia-Servicio en Salud",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      suppressHydrationWarning
      className={`${sourceSans.variable} ${lexend.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
