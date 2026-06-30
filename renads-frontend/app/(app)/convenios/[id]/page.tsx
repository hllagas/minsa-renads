"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { conventionHooks } from "@/lib/convenios/hooks";
import { FLOW_ACTIONS } from "@/lib/convenios/flow-actions";
import {
  useCamposClinicos,
  useHistorial,
  useParticipantes,
} from "@/lib/convenios/flow";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { PageHeader } from "@/components/data/page-header";
import { FlowActionDialog } from "@/components/crud/flow-action-dialog";
import { SimpleObjectTable } from "@/components/data/simple-object-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

function Dato({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid gap-0.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm">{value ?? "—"}</dd>
    </div>
  );
}

export default function ConvenioDetallePage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const user = useAuthStore((s) => s.user);

  const { data: c, isLoading, isError } = conventionHooks.useDetail(id);
  const campos = useCamposClinicos(id);
  const participantes = useParticipantes(id);
  const historial = useHistorial(id);

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Cargando convenio…</p>;
  }
  if (isError || !c) {
    return <p className="text-sm text-destructive">No se pudo cargar el convenio.</p>;
  }

  const esEspecifico = /espec/i.test(c.tipo_convenio);
  const acciones = FLOW_ACTIONS.filter(
    (a) =>
      userHasRole(user, ...a.roles) && (!a.onlyEspecifico || esEspecifico),
  );

  return (
    <div>
      <div className="mb-4">
        <Link
          href="/convenios"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Convenios
        </Link>
      </div>
      <PageHeader
        title={c.titulo}
        description={c.codigo || undefined}
        actions={
          <Button
            variant="outline"
            render={<Link href={`/convenios/${c.id}/editar`}>Editar</Link>}
          />
        }
      />

      {acciones.length ? (
        <div className="mb-6 flex flex-wrap gap-2">
          {acciones.map((a) => (
            <FlowActionDialog
              key={a.key}
              endpoint="conventions"
              resourceId={c.id}
              action={a}
            />
          ))}
        </div>
      ) : null}

      <Tabs defaultValue="datos">
        <TabsList>
          <TabsTrigger value="datos">Datos</TabsTrigger>
          <TabsTrigger value="campos">Campos clínicos</TabsTrigger>
          <TabsTrigger value="participantes">Participantes</TabsTrigger>
          <TabsTrigger value="historial">Historial</TabsTrigger>
        </TabsList>

        <TabsContent value="datos">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Datos del convenio
                <Badge variant="secondary">{c.estado_actual}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
                <Dato label="Tipo" value={c.tipo_convenio} />
                <Dato label="Estado" value={`${c.estado_actual} (${c.estado_codigo})`} />
                <Dato label="Solicitante" value={c.solicitante} />
                <Dato
                  label="Órgano regional"
                  value={
                    c.organo_regional_nombre
                      ? `${c.organo_regional_nombre}${c.tipo_organo_regional ? ` (${c.tipo_organo_regional})` : ""}`
                      : "—"
                  }
                />
                <Dato
                  label="Universidad"
                  value={
                    c.universidad_nombre
                      ? `${c.universidad_nombre}${c.tipo_entidad_universidad ? ` (${c.tipo_entidad_universidad})` : ""}`
                      : "—"
                  }
                />
                <Dato label="Fecha de solicitud" value={c.fecha_solicitud} />
                <Dato label="Inicio de vigencia" value={c.fecha_inicio} />
                <Dato label="Fin de vigencia" value={c.fecha_fin} />
                <Dato label="Máx. campos clínicos" value={c.max_campos_clinicos} />
              </dl>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="campos">
          <SimpleObjectTable
            columns={[
              { key: "ipress", header: "IPRESS" },
              { key: "carrera_profesional", header: "Carrera" },
              { key: "especialidad", header: "Especialidad" },
              { key: "cantidad_maxima", header: "Cant. máx." },
              { key: "vigencia_inicio", header: "Vig. inicio" },
              { key: "vigencia_fin", header: "Vig. fin" },
            ]}
            rows={campos.data ?? []}
            emptyMessage="Sin campos clínicos."
          />
        </TabsContent>

        <TabsContent value="participantes">
          <SimpleObjectTable
            columns={[
              { key: "tipo_contenido", header: "Tipo entidad" },
              { key: "id_objeto", header: "Id entidad" },
              { key: "tipo_autoridad_firmante", header: "Autoridad firmante" },
              { key: "es_firmante", header: "Firmante" },
            ]}
            rows={participantes.data ?? []}
            emptyMessage="Sin participantes."
          />
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
