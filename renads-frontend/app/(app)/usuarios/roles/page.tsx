"use client";

import Link from "next/link";

import { groupsConfig } from "@/lib/usuarios/configs";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { UsuariosAccessGuard } from "@/components/usuarios/access-guard";

/** Roles / Grupos — CRUD con asignación múltiple de permisos. Solo superusuario. */
export default function RolesPage() {
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
        <ResourceCrud config={groupsConfig} />
      </UsuariosAccessGuard>
    </div>
  );
}
