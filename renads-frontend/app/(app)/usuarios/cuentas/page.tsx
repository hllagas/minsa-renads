"use client";

import Link from "next/link";
import { useState } from "react";

import { usersConfig } from "@/lib/usuarios/configs";
import type { User } from "@/lib/usuarios/types";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { UsuariosAccessGuard } from "@/components/usuarios/access-guard";
import { SetPasswordDialog } from "@/components/usuarios/set-password-dialog";
import { AssignProfilesDialog } from "@/components/usuarios/assign-profiles-dialog";

/** Cuentas de usuario — CRUD + contraseña + asignación de alcance. Solo superusuario. */
export default function CuentasPage() {
  // La página posee los diálogos (estado del usuario objetivo de cada uno).
  const [passwordTarget, setPasswordTarget] = useState<User | null>(null);
  const [profilesTarget, setProfilesTarget] = useState<User | null>(null);

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
          config={usersConfig}
          rowActions={[
            {
              key: "assign-profiles",
              label: "Entidades",
              onClick: (row) => setProfilesTarget(row),
            },
            {
              key: "set-password",
              label: "Contraseña",
              onClick: (row) => setPasswordTarget(row),
            },
          ]}
        />
        <SetPasswordDialog
          user={passwordTarget}
          onClose={() => setPasswordTarget(null)}
        />
        <AssignProfilesDialog
          user={profilesTarget}
          onClose={() => setProfilesTarget(null)}
        />
      </UsuariosAccessGuard>
    </div>
  );
}
