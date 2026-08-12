"use client";

import Link from "next/link";

import { userEntityProfilesConfig } from "@/lib/usuarios/configs";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { UsuariosAccessGuard } from "@/components/usuarios/access-guard";

/**
 * Perfiles institucionales — vista global (list + filtros + editar `activo` + eliminar).
 * El **alta** se realiza por usuario desde *Cuentas → Entidades* (solo superusuario), que consume
 * el sub-recurso `users/{id}/profiles/`. Aquí no se crean perfiles fila a fila.
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
        <div className="mb-4 rounded-md border p-3 text-sm text-muted-foreground">
          Para asignar el alcance de un usuario, usa{" "}
          <Link href="/usuarios/cuentas" className="font-medium underline">
            Cuentas → Entidades
          </Link>{" "}
          (solo superusuario). Esta vista es la lista global de perfiles.
        </div>
        <ResourceCrud config={userEntityProfilesConfig} />
      </UsuariosAccessGuard>
    </div>
  );
}
