"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { conventionHooks, type ConventionWrite } from "@/lib/convenios/hooks";
import { extractApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/data/page-header";
import { ConvenioCreateForm } from "@/components/convenios/convenio-create-form";
import { Card, CardContent } from "@/components/ui/card";

export default function NuevoConvenioPage() {
  const router = useRouter();
  const createM = conventionHooks.useCreate();

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="Nuevo convenio" />
      <Card>
        <CardContent className="pt-6">
          <ConvenioCreateForm
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
