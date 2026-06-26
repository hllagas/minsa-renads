"use client";

import { useResourceSubList } from "@/lib/api/flow";
import type { RotationRead } from "@/lib/internados/hooks";
import { ROTATION_ACTIONS } from "@/lib/internados/flow-actions";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { FlowActionDialog } from "@/components/crud/flow-action-dialog";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

/** Lista de rotaciones de un internado con sus acciones de flujo (gateadas por rol). */
export function RotationsPanel({ internshipId }: { internshipId: number }) {
  const user = useAuthStore((s) => s.user);
  const { data, isLoading, isError } = useResourceSubList<RotationRead>(
    "internships",
    internshipId,
    "rotaciones",
  );

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Cargando rotaciones…</p>;
  }
  if (isError) {
    return <p className="text-sm text-destructive">No se pudieron cargar las rotaciones.</p>;
  }
  if (!data?.length) {
    return <p className="text-sm text-muted-foreground">Sin rotaciones.</p>;
  }

  return (
    <div className="grid gap-3">
      {data.map((r) => {
        const acciones = ROTATION_ACTIONS.filter((a) => userHasRole(user, ...a.roles));
        return (
          <Card key={r.id}>
            <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-6">
              <div className="grid gap-0.5 text-sm">
                <div className="flex items-center gap-2 font-medium">
                  Rotación #{r.numero_rotacion}
                  <Badge variant="secondary">{r.estado_actual}</Badge>
                </div>
                <div className="text-muted-foreground">
                  {r.fecha_inicio} → {r.fecha_fin}
                </div>
              </div>
              {acciones.length ? (
                <div className="flex flex-wrap gap-2">
                  {acciones.map((a) => (
                    <FlowActionDialog
                      key={a.key}
                      endpoint="rotations"
                      resourceId={r.id}
                      action={a}
                    />
                  ))}
                </div>
              ) : null}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
