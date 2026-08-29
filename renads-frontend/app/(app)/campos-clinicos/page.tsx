"use client";

import Link from "next/link";

import { PageHeader } from "@/components/data/page-header";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/**
 * Índice de Campos Clínicos: dos sub-módulos del módulo Convenios.
 * - Registro (CONAPRES): total por sede docente + carrera.
 * - Asignación (Órgano Regional): cupos por universidad contra un registro.
 * El acceso de escritura lo controla el backend por rol; el nav ya restringe la visibilidad.
 */
const CARDS = [
  {
    href: "/campos-clinicos/registros",
    title: "Determinación de campos de formación",
    description:
      "Campos de formación determinados a cada sede docente y carrera profesional (CONAPRES).",
  },
  {
    href: "/campos-clinicos/asignaciones",
    title: "Asignación de campos de formación",
    description:
      "Campos de formación asignados a cada universidad, según disponibilidad en cada sede docente (Órgano Regional).",
  },
];

export default function CamposClinicosPage() {
  return (
    <div className="grid gap-8">
      <PageHeader
        title="Campos de formación"
        description="Determinación y Registro (CONAPRES) y asignación por universidad (Órgano Regional)."
      />
      <div className="grid gap-4 sm:grid-cols-2">
        {CARDS.map((c) => (
          <Link key={c.href} href={c.href}>
            <Card className="h-full transition-colors hover:bg-muted/50">
              <CardHeader>
                <CardTitle>{c.title}</CardTitle>
                <CardDescription>{c.description}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
