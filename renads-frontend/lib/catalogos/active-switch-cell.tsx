"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";
import { extractApiError } from "@/lib/api/errors";
import { Switch } from "@/components/ui/switch";

/**
 * Switch inline que hace PATCH `{activo}` directamente e invalida el listado del recurso.
 * Diseñado para usarse como `render` de una `ColumnConfig` en `ResourceConfig`.
 */
export function ActiveSwitchCell({
  row,
  endpoint,
}: {
  row: WithId;
  endpoint: string;
}) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (newValue: boolean) =>
      api.patch(`/${endpoint}/${row.id}/`, { activo: newValue }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [endpoint] });
    },
    onError: (err) => toast.error(extractApiError(err)),
  });

  return (
    <Switch
      checked={!!row.activo}
      onCheckedChange={(checked) => mutation.mutate(checked)}
      disabled={mutation.isPending}
      aria-label={row.activo ? "Desactivar" : "Activar"}
    />
  );
}
