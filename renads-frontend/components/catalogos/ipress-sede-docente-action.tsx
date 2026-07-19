"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { useResourceAction } from "@/lib/api/flow";
import { resourceKeys } from "@/lib/api/query";
import { extractApiError } from "@/lib/api/errors";
import type { WithId } from "@/lib/api/query";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

/**
 * Acción CONAPRES para autorizar/revocar una IPRESS como sede docente
 * (`POST /ipress/{id}/autorizar-sede-docente/`, body `{ autorizar }`). Al éxito refresca la lista
 * de IPRESS (la columna «Sede docente» cambia). El gating de rol vive en la página.
 */
export function IpressSedeDocenteAction({ row }: { row: WithId }) {
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();
  const yaEsSede = Boolean(row.es_sede_docente);
  const autorizar = !yaEsSede;
  const actionM = useResourceAction(
    "ipress",
    row.id,
    "autorizar-sede-docente",
  );

  const label = yaEsSede ? "Revocar sede docente" : "Autorizar sede docente";

  function onConfirm() {
    actionM.mutate(
      { autorizar },
      {
        onSuccess: () => {
          // `useResourceAction` solo invalida el detalle/flujo: refrescar además la lista.
          qc.invalidateQueries({ queryKey: resourceKeys.all("ipress") });
          toast.success(
            autorizar ? "IPRESS autorizada como sede docente." : "Autorización de sede docente revocada.",
          );
          setOpen(false);
        },
        onError: (e) => toast.error(extractApiError(e)),
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <Button variant="outline" size="sm">
            {label}
          </Button>
        }
      />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{label}</DialogTitle>
          <DialogDescription>
            {autorizar
              ? "Al autorizar, esta IPRESS podrá usarse como sede docente en campos clínicos de convenios."
              : "Al revocar, esta IPRESS dejará de estar disponible como sede docente en nuevos campos clínicos."}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={actionM.isPending}
          >
            Cancelar
          </Button>
          <Button onClick={onConfirm} disabled={actionM.isPending}>
            {actionM.isPending ? "Procesando…" : "Confirmar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
