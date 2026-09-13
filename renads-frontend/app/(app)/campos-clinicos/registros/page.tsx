"use client";

import Link from "next/link";

import { DeterminacionView } from "@/components/campos-clinicos/determinacion-view";

export default function RegistrosCamposClinicosPage() {
  return (
    <div>
      <div className="mb-4">
        <Link
          href="/campos-clinicos"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Campos de formación
        </Link>
        <h1 className="mt-1 text-xl font-semibold">
          Determinación de campos de formación
        </h1>
      </div>
      <DeterminacionView />
    </div>
  );
}
