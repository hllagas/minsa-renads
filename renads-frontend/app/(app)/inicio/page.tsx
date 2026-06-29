"use client";

import { useAuthStore } from "@/lib/auth/store";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/**
 * Home protegida (placeholder). Confirma la sesión end-to-end mostrando los datos reales de
 * `me` (nombre, roles y perfiles institucionales). Se reemplazará por el dashboard real.
 */
export default function HomePage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Bienvenido, {user?.nombre}</h1>
        <p className="text-muted-foreground">Sistema del Registro Nacional de Articulación Docencia-Servicio en Salud- RENADS</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Roles</CardTitle>
            <CardDescription>Grupos del usuario actual.</CardDescription>
          </CardHeader>
          <CardContent>
            {user?.grupos.length ? (
              <ul className="list-inside list-disc text-sm">
                {user.grupos.map((g) => (
                  <li key={g}>{g}</li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">Sin roles asignados.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Perfiles institucionales</CardTitle>
            <CardDescription>Entidades dentro de tu ámbito.</CardDescription>
          </CardHeader>
          <CardContent>
            {user?.perfiles.length ? (
              <ul className="grid gap-1 text-sm">
                {user.perfiles.map((p, i) => (
                  <li key={`${p.tipo_entidad}-${p.id_objeto}-${i}`}>
                    <span className="font-medium">{p.entidad}</span>{" "}
                    <span className="text-muted-foreground">({p.rol})</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">Sin perfiles institucionales.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
