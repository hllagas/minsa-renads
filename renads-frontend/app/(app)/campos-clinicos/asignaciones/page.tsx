"use client";

import Link from "next/link";

import { clinicalFieldAllocationsConfig } from "@/lib/convenios/clinical-fields";
import { ResourceCrud } from "@/components/crud/resource-crud";

/** Asignación de campos clínicos por universidad (escritura Órgano Regional; backend `IsRegionalOrganOrReadOnly`). */
export default function AsignacionesCamposClinicosPage() {
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
      <ResourceCrud config={clinicalFieldAllocationsConfig} />
    </div>
  );
}
