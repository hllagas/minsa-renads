"use client";

import type { ReactNode } from "react";
import { CalendarX2 } from "lucide-react";

import { moduloBloqueado, useAuthStore } from "@/lib/auth/store";

/**
 * Guard temporal de módulo (UX). Comprueba si el usuario tiene el módulo fuera
 * de su ventana de calendario (`modulos_bloqueados` de `/auth/me/`). Si está
 * bloqueado, muestra "Módulo no disponible"; si no, renderiza los hijos.
 *
 * Admite múltiples content-types: basta que UNO esté bloqueado para activar
 * el aviso. Admin RENADS y superusuario siempre ven el contenido (exentos).
 * La autoridad final es el backend (`IsModuleEnabled`); este gate es UX.
 */
export function ModuleGate({
  contentTypes,
  children,
}: {
  /** Content types (app_label + model) que gobiernan este módulo. */
  contentTypes: { appLabel: string; model: string }[];
  children: ReactNode;
}) {
  const user = useAuthStore((s) => s.user);
  const bloqueado = contentTypes.some((ct) => moduloBloqueado(user, ct.appLabel, ct.model));

  if (!bloqueado) return <>{children}</>;

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
      <CalendarX2 className="size-12 text-muted-foreground/50" />
      <div className="grid gap-1">
        <h2 className="text-lg font-semibold">Módulo fuera de su ventana de registro</h2>
        <p className="max-w-sm text-sm text-muted-foreground">
          Este módulo solo está habilitado durante el periodo programado en el Calendario de
          actividades. Consulta con el Administrador RENADS.
        </p>
      </div>
    </div>
  );
}
