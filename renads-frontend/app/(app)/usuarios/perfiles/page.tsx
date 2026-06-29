"use client";

import Link from "next/link";

import { userEntityProfilesConfig } from "@/lib/usuarios/configs";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { UsuariosAccessGuard } from "@/components/usuarios/access-guard";

/**
 * Perfiles institucionales — v1 parcial (list + filtros + editar `activo` + eliminar).
 * Escritura `Administrador RENADS` o superusuario. Alta diferida a v2 (falta `content-types`).
 */
export default function PerfilesPage() {
  return (
    <div>
      <div className="mb-4">
        <Link
          href="/usuarios"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Gestión de Usuarios
        </Link>
      </div>
      <UsuariosAccessGuard access="admin">
        <div className="mb-4 rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm">
          El alta de perfiles está deshabilitada temporalmente (pendiente del endpoint{" "}
          <code>content-types</code> del backend).
        </div>
        <ResourceCrud config={userEntityProfilesConfig} />
      </UsuariosAccessGuard>
    </div>
  );
}
