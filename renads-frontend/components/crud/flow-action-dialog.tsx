"use client";

import { useState } from "react";
import { toast } from "sonner";

import type { FlowAction } from "@/lib/crud/flow-action";
import { useResourceAction } from "@/lib/api/flow";
import { extractApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ResourceForm } from "@/components/crud/resource-form";

/**
 * Botón + diálogo de una acción de flujo sobre un recurso (`/{endpoint}/{id}/{action}/`).
 * Genérico: convenios, internados, rotaciones. Asume que el rol ya fue verificado por el llamador.
 */
export function FlowActionDialog({
  endpoint,
  resourceId,
  action,
  size = "sm",
}: {
  endpoint: string;
  resourceId: number;
  action: FlowAction;
  size?: "sm" | "default";
}) {
  const [open, setOpen] = useState(false);
  const mutation = useResourceAction(endpoint, resourceId, action.key);

  return (
    <>
      <Button variant="outline" size={size} onClick={() => setOpen(true)}>
        {action.label}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{action.label}</DialogTitle>
          </DialogHeader>
          <ResourceForm
            fields={action.fields}
            initial={null}
            submitting={mutation.isPending}
            onCancel={() => setOpen(false)}
            onSubmit={(payload) =>
              mutation.mutate(payload, {
                onSuccess: () => {
                  toast.success(`${action.label}: registrado.`);
                  setOpen(false);
                },
                onError: (e) => toast.error(extractApiError(e)),
              })
            }
          />
        </DialogContent>
      </Dialog>
    </>
  );
}
