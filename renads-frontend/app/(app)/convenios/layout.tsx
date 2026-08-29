"use client";

import type { ReactNode } from "react";
import { ModuleGate } from "@/components/auth/module-gate";

/** Gate temporal: bloquea el módulo Convenios cuando está fuera de su ventana de calendario. */
export default function ConveniosLayout({ children }: { children: ReactNode }) {
  return (
    <ModuleGate contentTypes={[{ appLabel: "convenios", model: "convention" }]}>
      {children}
    </ModuleGate>
  );
}
