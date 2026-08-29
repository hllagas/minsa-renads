"use client";

import type { ReactNode } from "react";
import { ModuleGate } from "@/components/auth/module-gate";

/** Gate temporal: bloquea el módulo Internados cuando está fuera de su ventana de calendario. */
export default function InternadosLayout({ children }: { children: ReactNode }) {
  return (
    <ModuleGate
      contentTypes={[
        { appLabel: "internados", model: "internship" },
        { appLabel: "internados", model: "student" },
      ]}
    >
      {children}
    </ModuleGate>
  );
}
