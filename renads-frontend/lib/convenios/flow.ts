"use client";

import { useResourceAction, useResourceSubList } from "@/lib/api/flow";
import { useQuery } from "@tanstack/react-query";
import { fetchAllPages } from "@/lib/dashboard/fetch-all";

const CONV = "conventions";

/** Acción de flujo del convenio (`conventions/{id}/{action}/`). */
export const useFlowAction = (id: number, action: string) =>
  useResourceAction(CONV, id, action);

/** Campos clínicos registrados para el convenio (endpoint independiente). */
export const useCamposClinicos = (id: number) =>
  useQuery({
    queryKey: ["clinical-field-registrations", "by-convenio", id],
    queryFn: () => fetchAllPages("clinical-field-registrations", { convenio: String(id) }),
    enabled: id > 0,
    staleTime: 60_000,
  });

/** Partes firmantes del convenio (`conventions/{id}/parties`). */
export const usePartes = (id: number) =>
  useResourceSubList(CONV, id, "parties");

export const useParticipantes = (id: number) =>
  useResourceSubList(CONV, id, "participantes");
export const useHistorial = (id: number) => useResourceSubList(CONV, id, "historial");
