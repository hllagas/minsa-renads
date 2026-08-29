"use client";

import type { ReactNode } from "react";
import { ModuleGate } from "@/components/auth/module-gate";

/** Gate temporal: bloquea el módulo Actividades cuando está fuera de su ventana de calendario. */
export default function ActividadesLayout({ children }: { children: ReactNode }) {
  return (
    <ModuleGate contentTypes={[{ appLabel: "actividades", model: "teachingactivity" }]}>
      {children}
    </ModuleGate>
  );
}
