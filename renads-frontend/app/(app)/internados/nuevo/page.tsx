"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { internshipHooks, type InternshipWrite } from "@/lib/internados/hooks";
import { INTERNSHIP_FIELDS } from "@/lib/internados/internship-fields";
import { extractApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/data/page-header";
import { ResourceForm } from "@/components/crud/resource-form";
import { Card, CardContent } from "@/components/ui/card";

export default function NuevoInternadoPage() {
  const router = useRouter();
  const createM = internshipHooks.useCreate();

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Nuevo internado" />
      <Card>
        <CardContent className="pt-6">
          <ResourceForm
            fields={INTERNSHIP_FIELDS}
            initial={null}
            submitting={createM.isPending}
            onCancel={() => router.push("/internados")}
            onSubmit={(payload) =>
              createM.mutate(payload as InternshipWrite, {
                onSuccess: (it) => {
                  toast.success("Internado creado.");
                  router.push(`/internados/${it.id}`);
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
