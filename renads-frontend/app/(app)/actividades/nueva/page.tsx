"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import {
  teachingActivityHooks,
  type TeachingActivityWrite,
} from "@/lib/actividades/hooks";
import { ACTIVITY_FIELDS } from "@/lib/actividades/activity-fields";
import { extractApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/data/page-header";
import { ResourceForm } from "@/components/crud/resource-form";
import { Card, CardContent } from "@/components/ui/card";

export default function NuevaActividadPage() {
  const router = useRouter();
  const createM = teachingActivityHooks.useCreate();

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Nueva actividad" />
      <Card>
        <CardContent className="pt-6">
          <ResourceForm
            fields={ACTIVITY_FIELDS}
            initial={null}
            submitting={createM.isPending}
            onCancel={() => router.push("/actividades")}
            onSubmit={(payload) =>
              createM.mutate(payload as TeachingActivityWrite, {
                onSuccess: (a) => {
                  toast.success("Actividad registrada.");
                  router.push(`/actividades/${a.id}`);
                },
                onError: (e) => toast.error(extractApiError(e)),
              })
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}
