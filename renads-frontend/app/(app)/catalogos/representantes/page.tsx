"use client";

import Link from "next/link";

import { REPRESENTATIVES_CONFIG } from "@/lib/catalogos/representatives";
import { ResourceCrud } from "@/components/crud/resource-crud";

/** Representantes (CRUD polimórfico) — v1: list + filtros + editar + eliminar (alta diferida a v2). */
export default function RepresentantesPage() {
  return (
    <div>
      <div className="mb-4">
        <Link
          href="/catalogos"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Catálogos
        </Link>
      </div>
      <ResourceCrud config={REPRESENTATIVES_CONFIG} />
    </div>
  );
}
