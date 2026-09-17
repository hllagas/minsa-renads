"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { internshipHooks, type InternshipWrite } from "@/lib/internados/hooks";
import { buildInternshipFields } from "@/lib/internados/internship-fields";
import { extractApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/data/page-header";
import { ResourceForm } from "@/components/crud/resource-form";
import { Card, CardContent } from "@/components/ui/card";

export default function NuevoInternadoPage() {
  const router = useRouter();
  const createM = internshipHooks.useCreate();

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Nuevo interno" />
      <Card>
        <CardContent className="pt-6">
          <ResourceForm
            fields={buildInternshipFields(null)}
            initial={null}
            submitting={createM.isPending}
            onCancel={() => router.back()}
            onSubmit={(payload) =>
              createM.mutate(payload as InternshipWrite, {
                onSuccess: () => {
                  toast.success("Interno creado.");
                  router.back();
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
