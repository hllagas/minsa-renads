"use client";

import Image from "next/image";

import { useAuthStore } from "@/lib/auth/store";

export default function HomePage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold">Bienvenido, {user?.nombre}</h1>
        <p className="text-muted-foreground">
          Sistema del Registro Nacional de Articulación Docencia-Servicio en Salud — RENADS
        </p>
      </div>

      <div
        className="relative w-full overflow-hidden rounded-lg border bg-muted/10"
        style={{ height: "calc(100dvh - 11rem)" }}
      >
        <Image
          src="/Gantt_Internado_2027.jpg"
          alt="Cronograma Gantt — Internado 2027"
          fill
          className="object-contain"
          priority
        />
      </div>
    </div>
  );
}
