"use client";

import { useRouter, useParams } from "next/navigation";
import { toast } from "sonner";

import { internshipHooks, type InternshipWrite } from "@/lib/internados/hooks";
import { INTERNSHIP_EDIT_FIELDS } from "@/lib/internados/internship-fields";
import { extractApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/data/page-header";
import { ResourceForm } from "@/components/crud/resource-form";
import { Card, CardContent } from "@/components/ui/card";

export default function EditarInternadoPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  const { data: it, isLoading } = internshipHooks.useDetail(id);
  const updateM = internshipHooks.useUpdate();

  if (isLoading || !it) {
    return <p className="text-sm text-muted-foreground">Cargando internado…</p>;
  }

  const initial = {
    ipress: null, // el read da el nombre, no el id; se reasigna solo si se cambia
    fecha_inicio: it.fecha_inicio,
    fecha_fin: it.fecha_fin,
    observaciones: it.observaciones ?? "",
  };

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Editar internado" />
      <Card>
        <CardContent className="pt-6">
          <ResourceForm
            fields={INTERNSHIP_EDIT_FIELDS}
            initial={initial}
            submitting={updateM.isPending}
            onCancel={() => router.push(`/internados/${id}`)}
            onSubmit={(payload) =>
              updateM.mutate(
                { id, payload: payload as Partial<InternshipWrite> },
                {
                  onSuccess: () => {
                    toast.success("Cambios guardados.");
                    router.push(`/internados/${id}`);
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
