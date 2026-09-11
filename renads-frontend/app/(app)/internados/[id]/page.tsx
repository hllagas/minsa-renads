"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { internshipHooks } from "@/lib/internados/hooks";
import { INTERNSHIP_ACTIONS } from "@/lib/internados/flow-actions";
import { useResourceSubList } from "@/lib/api/flow";
import { extractApiError } from "@/lib/api/errors";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { PageHeader } from "@/components/data/page-header";
import { FlowActionDialog } from "@/components/crud/flow-action-dialog";
import { RotationsPanel } from "@/components/internados/rotations-panel";
import { SimpleObjectTable } from "@/components/data/simple-object-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

function Dato({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid gap-0.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm">{value ?? "—"}</dd>
    </div>
  );
}

export default function InternadoDetallePage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const user = useAuthStore((s) => s.user);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const { data: it, isLoading, isError } = internshipHooks.useDetail(id);
  const historial = useResourceSubList("interns", id, "historial");
  const removeM = internshipHooks.useRemove();

  const canDelete = userHasRole(user, "Universidad", "Administrador RENADS");

  function confirmDelete() {
    removeM.mutate(id, {
      onSuccess: () => {
        toast.success("Interno eliminado. El cupo queda disponible nuevamente.");
        setDeleteOpen(false);
        router.back();
      },
      onError: (e) => toast.error(extractApiError(e)),
    });
  }

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Cargando internado…</p>;
  }
  if (isError || !it) {
    return <p className="text-sm text-destructive">No se pudo cargar el internado.</p>;
  }

  const acciones = INTERNSHIP_ACTIONS.filter((a) => userHasRole(user, ...a.roles));

  return (
    <div>
      <div className="mb-4">
        <button
          onClick={() => router.back()}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Internos
        </button>
      </div>
      <PageHeader
        title={`Internado de ${it.estudiante}`}
        description={it.convenio}
        actions={
          <div className="flex items-center gap-2">
            {canDelete ? (
              <Button variant="destructive" onClick={() => setDeleteOpen(true)}>
                Eliminar
              </Button>
            ) : null}
            <Button
              variant="outline"
              render={<Link href={`/internados/${it.id}/editar`}>Editar</Link>}
            />
          </div>
        }
      />

      {acciones.length ? (
        <div className="mb-6 flex flex-wrap gap-2">
          {acciones.map((a) => (
            <FlowActionDialog
              key={a.key}
              endpoint="interns"
              resourceId={it.id}
              action={a}
            />
          ))}
        </div>
      ) : null}

      <Tabs defaultValue="datos">
        <TabsList>
          <TabsTrigger value="datos">Datos</TabsTrigger>
          <TabsTrigger value="rotaciones">Rotaciones</TabsTrigger>
          <TabsTrigger value="historial">Historial</TabsTrigger>
        </TabsList>

        <TabsContent value="datos">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Datos del internado
                <Badge variant="secondary">{it.estado_actual}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-4 md:grid-cols-3">
                <Dato label="Estudiante" value={it.estudiante} />
                <Dato label="Convenio" value={it.convenio} />
                <Dato label="Sede (IPRESS)" value={it.ipress} />
                <Dato label="Tutor" value={it.tutor} />
                <Dato label="Estado" value={`${it.estado_actual} (${it.estado_codigo})`} />
                <Dato
                  label="Declaraciones juradas"
                  value={
                    it.estado_declaraciones ? (
                      <Badge
                        variant={
                          it.estado_declaraciones === "VALIDADAS"
                            ? "default"
                            : it.estado_declaraciones === "OBSERVADAS"
                              ? "destructive"
                              : "secondary"
                        }
                      >
                        {it.estado_declaraciones}
                      </Badge>
                    ) : (
                      "—"
                    )
                  }
                />
                <Dato label="Inicio" value={it.fecha_inicio} />
                <Dato label="Fin" value={it.fecha_fin} />
                <Dato label="Observaciones" value={it.observaciones} />
              </dl>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="rotaciones">
          <RotationsPanel internId={it.id} />
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

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar interno</DialogTitle>
            <DialogDescription>
              Esta acción elimina el registro de internado de{" "}
              <strong>{it.estudiante}</strong> y restablece el cupo de asignación de campos de
              formación a la sede docente y universidad. No se puede deshacer.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteOpen(false)}
              disabled={removeM.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={confirmDelete}
              disabled={removeM.isPending}
            >
              {removeM.isPending ? "Eliminando…" : "Eliminar interno"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
