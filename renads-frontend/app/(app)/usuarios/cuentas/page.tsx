"use client";

import Link from "next/link";
import { useState } from "react";

import { usersConfig } from "@/lib/usuarios/configs";
import type { User } from "@/lib/usuarios/types";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { UsuariosAccessGuard } from "@/components/usuarios/access-guard";
import { SetPasswordDialog } from "@/components/usuarios/set-password-dialog";

/** Cuentas de usuario — CRUD + acción de contraseña. Solo superusuario. */
export default function CuentasPage() {
  // La página posee el diálogo de contraseña (estado del usuario objetivo).
  const [target, setTarget] = useState<User | null>(null);

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
              key: "set-password",
              label: "Contraseña",
              onClick: (row) => setTarget(row),
            },
          ]}
        />
        <SetPasswordDialog user={target} onClose={() => setTarget(null)} />
      </UsuariosAccessGuard>
    </div>
  );
}
