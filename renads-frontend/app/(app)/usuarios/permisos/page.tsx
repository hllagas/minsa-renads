"use client";

import Link from "next/link";

import { permissionsConfig } from "@/lib/usuarios/configs";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { UsuariosAccessGuard } from "@/components/usuarios/access-guard";

/** Permisos — catálogo de Django en solo lectura. Solo superusuario. */
export default function PermisosPage() {
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
      <UsuariosAccessGuard access="superuser">
        <ResourceCrud config={permissionsConfig} />
      </UsuariosAccessGuard>
    </div>
  );
}
