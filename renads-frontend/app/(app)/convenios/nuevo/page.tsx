"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { conventionHooks, type ConventionWrite } from "@/lib/convenios/hooks";
import { CONVENTION_FIELDS } from "@/lib/convenios/convention-fields";
import { extractApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/data/page-header";
import { ResourceForm } from "@/components/crud/resource-form";
import { Card, CardContent } from "@/components/ui/card";

export default function NuevoConvenioPage() {
  const router = useRouter();
  const createM = conventionHooks.useCreate();

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Nuevo convenio" />
      <Card>
        <CardContent className="pt-6">
          <ResourceForm
            fields={CONVENTION_FIELDS}
            initial={null}
            submitting={createM.isPending}
            onCancel={() => router.push("/convenios")}
            onSubmit={(payload) =>
              createM.mutate(payload as ConventionWrite, {
                onSuccess: (conv) => {
                  toast.success("Convenio creado.");
                  router.push(`/convenios/${conv.id}`);
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
