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
      </div>
      <DeterminacionView />
    </div>
  );
}
