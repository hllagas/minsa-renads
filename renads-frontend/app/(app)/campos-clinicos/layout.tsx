"use client";

import type { ReactNode } from "react";
import { ModuleGate } from "@/components/auth/module-gate";

export default function CamposClinicosLayout({ children }: { children: ReactNode }) {
  return (
    <ModuleGate
      contentTypes={[
        { appLabel: "convenios", model: "clinicalfieldregistration" },
        { appLabel: "convenios", model: "clinicalfieldallocation" },
      ]}
    >
      {children}
    </ModuleGate>
  );
}
