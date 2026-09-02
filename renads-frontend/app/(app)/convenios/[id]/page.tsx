"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { conventionHooks } from "@/lib/convenios/hooks";
import { FLOW_ACTIONS } from "@/lib/convenios/flow-actions";
import {
  useCamposClinicos,
  useHistorial,
  useParticipantes,
  usePartes,
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

function detalleNombre(v: unknown): string {
  if (!v || typeof v !== "object") return "—";
  const obj = v as Record<string, unknown>;
  return String(obj.nombre ?? "—");
}

export default function ConvenioDetallePage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const user = useAuthStore((s) => s.user);

  const { data: c, isLoading, isError } = conventionHooks.useDetail(id);
  const campos = useCamposClinicos(id);
  const partes = usePartes(id);
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

  const vigEfectiva = (c as Record<string, unknown>).vigencia_efectiva as
    | { fecha_inicio?: string; fecha_fin?: string }
    | null
    | undefined;

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
        description={c.nomenclatura || undefined}
        actions={
          <Button
            variant="outline"
            render={<Link href={`/convenios/${c.id}/editar`}>Editar</Link>}
          />
        }
      />

      {(c as Record<string, unknown>).es_adenda ? (
        <Badge variant="outline" className="mb-3">Adenda</Badge>
      ) : null}

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
          <TabsTrigger value="partes">Partes firmantes</TabsTrigger>
          <TabsTrigger value="campos">Campos de formación</TabsTrigger>
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
                  label="Órgano del directorio"
                  value={
                    c.organo_directorio_nombre
                      ? `${c.organo_directorio_nombre}${c.tipo_organo_directorio ? ` (${c.tipo_organo_directorio})` : ""}`
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
                <Dato
                  label="Unidad ejecutora"
                  value={detalleNombre((c as Record<string, unknown>).unidad_ejecutora_detalle)}
                />
                <Dato
                  label="Facultad"
                  value={detalleNombre((c as Record<string, unknown>).facultad_detalle)}
                />
                <Dato label="Fecha de solicitud" value={c.fecha_solicitud} />
                <Dato label="Inicio de vigencia" value={c.fecha_inicio} />
                <Dato label="Fin de vigencia" value={c.fecha_fin} />
                {vigEfectiva ? (
                  <Dato
                    label="Vigencia efectiva"
                    value={`${vigEfectiva.fecha_inicio ?? "?"} – ${vigEfectiva.fecha_fin ?? "?"}`}
                  />
                ) : null}
                <Dato label="Máx. campos de formación" value={c.max_campos_clinicos} />
              </dl>

              {/* Adendas del convenio */}
              {Array.isArray((c as Record<string, unknown>).adendas) &&
              ((c as Record<string, unknown>).adendas as unknown[]).length > 0 ? (
                <div className="mt-6">
                  <h3 className="mb-2 text-sm font-medium">Adendas</h3>
                  <SimpleObjectTable
                    columns={[
                      { key: "titulo", header: "Título" },
                      { key: "estado_codigo", header: "Estado" },
                      { key: "fecha_inicio", header: "Inicio" },
                      { key: "fecha_fin", header: "Fin" },
                      {
                        key: "id",
                        header: "",
                        render: (row) => (
                          <Link
                            href={`/convenios/${(row as Record<string, unknown>).id}`}
                            className="text-sm text-primary hover:underline"
                          >
                            Ver
                          </Link>
                        ),
                      },
                    ]}
                    rows={(c as Record<string, unknown>).adendas as Record<string, unknown>[]}
                    emptyMessage="Sin adendas."
                  />
                </div>
              ) : null}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="partes">
          <SimpleObjectTable
            columns={[
              { key: "rol_display", header: "Rol" },
              {
                key: "organo_directorio_detalle",
                header: "Órgano",
                render: (row) => detalleNombre((row as Record<string, unknown>).organo_directorio_detalle),
              },
              {
                key: "organo_representante_detalle",
                header: "Representante",
                render: (row) => {
                  const d = (row as Record<string, unknown>).organo_representante_detalle as Record<string, unknown> | null;
                  return d ? String(d.nombre ?? "—") : "—";
                },
              },
              {
                key: "cargo_ejecutivo_detalle",
                header: "Cargo",
                render: (row) => {
                  const d = (row as Record<string, unknown>).cargo_ejecutivo_detalle as Record<string, unknown> | null;
                  return d ? String(d.nombre_masculino ?? "—") : "—";
                },
              },
              { key: "orden", header: "Orden" },
              {
                key: "es_firmante",
                header: "Firmante",
                render: (row) => ((row as Record<string, unknown>).es_firmante ? "Sí" : "No"),
              },
            ]}
            rows={partes.data ?? []}
            emptyMessage="Sin partes firmantes registradas."
          />
        </TabsContent>

        <TabsContent value="campos">
          <SimpleObjectTable
            columns={[
              {
                key: "ipress_detalle",
                header: "IPRESS",
                render: (row) => detalleNombre((row as Record<string, unknown>).ipress_detalle),
              },
              {
                key: "carrera_profesional_detalle",
                header: "Carrera",
                render: (row) => detalleNombre((row as Record<string, unknown>).carrera_profesional_detalle),
              },
              {
                key: "especialidad_detalle",
                header: "Especialidad",
                render: (row) => {
                  const d = (row as Record<string, unknown>).especialidad_detalle;
                  return d ? detalleNombre(d) : "—";
                },
              },
              { key: "campos_clinicos_registrados", header: "Registrados" },
              { key: "campos_clinicos_asignados", header: "Asignados" },
              { key: "disponibilidad", header: "Disponibles" },
              { key: "numero_resolucion_conapres", header: "N° Resolución" },
              { key: "fecha_resolucion_conapres", header: "Fecha resolución" },
            ]}
            rows={(campos.data?.results as Record<string, unknown>[] | undefined) ?? []}
            emptyMessage="Sin campos de formación."
          />
        </TabsContent>

        <TabsContent value="participantes">
          <SimpleObjectTable
            columns={[
              { key: "tipo_contenido", header: "Tipo entidad" },
              { key: "id_objeto", header: "Id entidad" },
              { key: "tipo_autoridad_firmante", header: "Autoridad firmante" },
              {
                key: "es_firmante",
                header: "Firmante",
                render: (row) => ((row as Record<string, unknown>).es_firmante ? "Sí" : "No"),
              },
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
