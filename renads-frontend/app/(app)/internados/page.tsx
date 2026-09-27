"use client";

import { PageHeader } from "@/components/data/page-header";

/**
 * Índice del módulo Internados. Las sub-opciones (Estudiantes, Tutores, Internos) se
 * navegan desde el acordeón del menú lateral. El cuerpo se definirá más adelante.
 */
export default function InternadosIndexPage() {
  return (
    <div className="grid gap-6">
      <PageHeader
        title="Internado"
        description="Gestión de estudiantes, tutores e internos."
      />
      <p className="text-sm text-muted-foreground">
        Selecciona una opción del menú lateral (Estudiantes, Tutores o Internos).
      </p>
    </div>
  );
}
