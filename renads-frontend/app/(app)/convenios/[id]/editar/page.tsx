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

  const fields = CONVENTION_EDIT_FIELDS;

  const initial = {
    titulo: c.titulo,
    nomenclatura: c.nomenclatura ?? "",
    plantilla: c.plantilla ?? null,
    convenio_marco: c.convenio_marco ?? null,
    solicitante_tipo_contenido: c.solicitante_tipo_contenido,
    solicitante_id_objeto: c.solicitante_id_objeto,
    organo_directorio: c.organo_directorio,
    gobierno_regional: c.gobierno_regional ?? null,
    universidad: c.universidad,
    unidad_ejecutora: c.unidad_ejecutora ?? null,
    facultad: c.facultad ?? null,
    fecha_solicitud: c.fecha_solicitud,
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
