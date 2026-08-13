"use client";

import Link from "next/link";

import { groupsConfig } from "@/lib/usuarios/configs";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { UsuariosAccessGuard } from "@/components/usuarios/access-guard";
import { RolePermissionMatrixForm } from "@/components/usuarios/role-permission-matrix-form";

/** Roles / Grupos — CRUD con matriz de permisos (app → modelo → acciones). Solo superusuario. */
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
        <ResourceCrud
          config={groupsConfig}
          dialogClassName="sm:max-w-3xl"
          renderForm={({ editing, submitting, onSubmit, onCancel }) => (
            <RolePermissionMatrixForm
              initial={editing}
              submitting={submitting}
              onSubmit={onSubmit}
              onCancel={onCancel}
            />
          )}
        />
      </UsuariosAccessGuard>
    </div>
  );
}
