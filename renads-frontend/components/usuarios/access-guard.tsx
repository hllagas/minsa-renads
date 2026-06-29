"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { isSuperuser, useAuthStore, userHasRole } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";

/**
 * Guard de ruta para `/usuarios`. `superuser` exige superusuario puro; `admin` admite superusuario
 * o `Administrador RENADS`. Si no se cumple, muestra «No autorizado» + enlace a `/usuarios` en vez
 * de renderizar el contenido. El gating del front es UX; el backend es la autoridad final.
 */
export function UsuariosAccessGuard({
  access,
  children,
}: {
  access: "superuser" | "admin";
  children: ReactNode;
}) {
  const user = useAuthStore((s) => s.user);
  const allowed =
    access === "superuser"
      ? isSuperuser(user)
      : isSuperuser(user) || userHasRole(user, "Administrador RENADS");

  if (!allowed) {
    return (
      <div className="grid gap-3">
        <h2 className="text-lg font-semibold">No autorizado</h2>
        <p className="text-sm text-muted-foreground">
          No tienes permisos para acceder a esta sección.
        </p>
        <Button
          variant="outline"
          className="w-fit"
          render={<Link href="/usuarios">Volver a Gestión de Usuarios</Link>}
        />
      </div>
    );
  }

  return <>{children}</>;
}
