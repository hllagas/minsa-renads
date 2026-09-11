"use client";

import Link from "next/link";

import { AsignacionView } from "@/components/campos-clinicos/asignacion-view";

/** Asignación de campos clínicos por universidad (escritura Órgano Regional; backend `IsRegionalOrganOrReadOnly`). */
export default function AsignacionesCamposClinicosPage() {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <Link
          href="/campos-clinicos"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Campos de formación
        </Link>
        <h1 className="mt-1 text-xl font-semibold">
          Asignación de campos de formación
        </h1>
      </div>
      <AsignacionView />
    </div>
  );
}
