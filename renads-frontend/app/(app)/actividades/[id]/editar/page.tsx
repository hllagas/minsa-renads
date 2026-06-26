"use client";

import { useRouter, useParams } from "next/navigation";
import { toast } from "sonner";

import {
  teachingActivityHooks,
  type TeachingActivityWrite,
} from "@/lib/actividades/hooks";
import { ACTIVITY_EDIT_FIELDS } from "@/lib/actividades/activity-fields";
import { extractApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/data/page-header";
import { ResourceForm } from "@/components/crud/resource-form";
import { Card, CardContent } from "@/components/ui/card";

export default function EditarActividadPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  const { data: a, isLoading } = teachingActivityHooks.useDetail(id);
  const updateM = teachingActivityHooks.useUpdate();

  if (isLoading || !a) {
    return <p className="text-sm text-muted-foreground">Cargando actividad…</p>;
  }

  const initial = {
    descripcion: a.descripcion ?? "",
    carga_horaria: a.carga_horaria ?? null,
    tipo_actividad: null, // el read da el nombre, no el id; se reasigna solo si se cambia
    servicio_area: a.servicio_area,
  };

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Editar actividad" />
      <Card>
        <CardContent className="pt-6">
          <ResourceForm
            fields={ACTIVITY_EDIT_FIELDS}
            initial={initial}
            submitting={updateM.isPending}
            onCancel={() => router.push(`/actividades/${id}`)}
            onSubmit={(payload) =>
              updateM.mutate(
                { id, payload: payload as Partial<TeachingActivityWrite> },
                {
                  onSuccess: () => {
                    toast.success("Cambios guardados.");
                    router.push(`/actividades/${id}`);
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
