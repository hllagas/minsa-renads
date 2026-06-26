"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { teachingActivityHooks } from "@/lib/actividades/hooks";
import { ACTIVITY_ACTIONS } from "@/lib/actividades/flow-actions";
import { useResourceSubList } from "@/lib/api/flow";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { PageHeader } from "@/components/data/page-header";
import { FlowActionDialog } from "@/components/crud/flow-action-dialog";
import { SimpleObjectTable } from "@/components/data/simple-object-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

function Dato({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid gap-0.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm">{value ?? "—"}</dd>
    </div>
  );
}

export default function ActividadDetallePage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const user = useAuthStore((s) => s.user);

  const { data: a, isLoading, isError } = teachingActivityHooks.useDetail(id);
  const historial = useResourceSubList("teaching-activities", id, "historial");

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Cargando actividad…</p>;
  }
  if (isError || !a) {
    return <p className="text-sm text-destructive">No se pudo cargar la actividad.</p>;
  }

  const acciones = ACTIVITY_ACTIONS.filter((ac) => userHasRole(user, ...ac.roles));

  return (
    <div>
      <div className="mb-4">
        <Link
          href="/actividades"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Actividades
        </Link>
      </div>
      <PageHeader
        title={`Actividad de ${a.interno}`}
        description={a.tipo_actividad}
        actions={
          <Button
            variant="outline"
            render={<Link href={`/actividades/${a.id}/editar`}>Editar</Link>}
          />
        }
      />

      {acciones.length ? (
        <div className="mb-6 flex flex-wrap gap-2">
          {acciones.map((ac) => (
            <FlowActionDialog
              key={ac.key}
              endpoint="teaching-activities"
              resourceId={a.id}
              action={ac}
            />
          ))}
        </div>
      ) : null}

      <Tabs defaultValue="datos">
        <TabsList>
          <TabsTrigger value="datos">Datos</TabsTrigger>
          <TabsTrigger value="historial">Historial</TabsTrigger>
        </TabsList>

        <TabsContent value="datos">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Datos de la actividad
                <Badge variant="secondary">{a.estado_actual}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
                <Dato label="Interno" value={a.interno} />
                <Dato label="Sede (IPRESS)" value={a.ipress} />
                <Dato label="Tutor" value={a.tutor} />
                <Dato label="Tipo" value={a.tipo_actividad} />
                <Dato label="Estado" value={`${a.estado_actual} (${a.estado_codigo})`} />
                <Dato label="Fecha" value={a.fecha_actividad} />
                <Dato label="Carga horaria" value={a.carga_horaria} />
                <Dato label="Descripción" value={a.descripcion} />
              </dl>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="historial">
          <SimpleObjectTable
            columns={[
              { key: "estado", header: "Estado" },
              { key: "estado_codigo", header: "Código" },
              { key: "cambiado_por", header: "Cambiado por" },
              { key: "cambiado_en", header: "Fecha" },
              { key: "observacion", header: "Observación" },
            ]}
            rows={historial.data ?? []}
            emptyMessage="Sin historial."
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
