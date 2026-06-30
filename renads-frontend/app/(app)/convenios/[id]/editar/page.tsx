"use client";

import { useRouter, useParams } from "next/navigation";
import { toast } from "sonner";

import { conventionHooks, type ConventionWrite } from "@/lib/convenios/hooks";
import { CONVENTION_EDIT_FIELDS } from "@/lib/convenios/convention-fields";
import { extractApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/data/page-header";
import { ResourceForm } from "@/components/crud/resource-form";
import { Card, CardContent } from "@/components/ui/card";

export default function EditarConvenioPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  const { data: c, isLoading } = conventionHooks.useDetail(id);
  const updateM = conventionHooks.useUpdate();

  if (isLoading || !c) {
    return <p className="text-sm text-muted-foreground">Cargando convenio…</p>;
  }

  // La nomenclatura (`codigo`) solo es editable cuando el convenio está en ENVIADO_VICEPAS.
  const nomenclaturaEditable = c.estado_codigo === "ENVIADO_VICEPAS";
  const fields = CONVENTION_EDIT_FIELDS.map((f) =>
    f.name === "codigo" ? { ...f, disabled: !nomenclaturaEditable } : f,
  );

  const initial = {
    titulo: c.titulo,
    codigo: c.codigo ?? "",
    plantilla: c.plantilla ?? null,
    convenio_marco: c.convenio_marco ?? null,
    solicitante_tipo_contenido: c.solicitante_tipo_contenido,
    solicitante_id_objeto: c.solicitante_id_objeto,
    organo_regional: c.organo_regional,
    universidad: c.universidad,
    fecha_solicitud: c.fecha_solicitud,
    fecha_inicio: c.fecha_inicio ?? "",
    max_campos_clinicos: c.max_campos_clinicos ?? null,
  };

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Editar convenio" description={c.titulo} />
      <Card>
        <CardContent className="pt-6">
          <ResourceForm
            fields={fields}
            initial={initial}
            submitting={updateM.isPending}
            onCancel={() => router.push(`/convenios/${id}`)}
            onSubmit={(payload) =>
              updateM.mutate(
                { id, payload: payload as Partial<ConventionWrite> },
                {
                  onSuccess: () => {
                    toast.success("Cambios guardados.");
                    router.push(`/convenios/${id}`);
                  },
                  onError: (e) => toast.error(extractApiError(e)),
                },
              )
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}
