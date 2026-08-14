"use client";

import Link from "next/link";

import { clinicalFieldRegistrationsConfig } from "@/lib/convenios/clinical-fields";
import { ResourceCrud } from "@/components/crud/resource-crud";

/** Registro de campos clínicos por sede + carrera (escritura CONAPRES; backend `IsConapresOrReadOnly`). */
export default function RegistrosCamposClinicosPage() {
  return (
    <div>
      <div className="mb-4">
        <Link
          href="/campos-clinicos"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Campos clínicos
        </Link>
      </div>
      <ResourceCrud config={clinicalFieldRegistrationsConfig} />
    </div>
  );
}
