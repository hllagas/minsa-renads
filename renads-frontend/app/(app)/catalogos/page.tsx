"use client";

import { PageHeader } from "@/components/data/page-header";

/**
 * Índice de Catálogos — mantenimiento de tablas maestras (Módulo 6). Las sub-opciones
 * (Entidades, Representantes, Tipología, Documentos, Auditoría) se navegan desde el
 * acordeón del menú lateral. El cuerpo se definirá más adelante.
 */
export default function CatalogosPage() {
  return (
    <div className="grid gap-6">
      <PageHeader
        title="Catálogos"
        description="Mantenimiento de tablas maestras del sistema."
      />
      <p className="text-sm text-muted-foreground">
        Selecciona una opción del menú lateral (Entidades, Representantes, Tipología,
        Documentos o Auditoría).
      </p>
    </div>
  );
}
