"use client";

import Link from "next/link";

import { USUARIOS_MENU, type UsuariosMenuItem } from "@/lib/usuarios/menu";
import { isSuperuser, useAuthStore, userHasRole } from "@/lib/auth/store";
import { PageHeader } from "@/components/data/page-header";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/** Tarjeta enlazada de una sección de Gestión de Usuarios. */
function LinkCard({ href, title, description }: UsuariosMenuItem) {
  return (
    <Link href={href}>
      <Card className="h-full transition-colors hover:bg-muted/50">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
      </Card>
    </Link>
  );
}

/** Índice de Gestión de Usuarios (Módulo 7). Las tarjetas se muestran según el acceso del usuario. */
export default function UsuariosPage() {
  const user = useAuthStore((s) => s.user);
  const superuser = isSuperuser(user);
  const admin = superuser || userHasRole(user, "Administrador RENADS");

  const visibles = USUARIOS_MENU.filter((item) =>
    item.access === "superuser" ? superuser : admin,
  );

  return (
    <div className="grid gap-8">
      <PageHeader
        title="Gestión de Usuarios"
        description="Administración de cuentas, roles, permisos y perfiles institucionales."
      />

      {visibles.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No tienes secciones disponibles en este módulo.
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {visibles.map((item) => (
            <LinkCard key={item.href} {...item} />
          ))}
        </div>
      )}
    </div>
  );
}
