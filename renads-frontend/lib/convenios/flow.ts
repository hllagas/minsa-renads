"use client";

import { useResourceAction, useResourceSubList } from "@/lib/api/flow";

const CONV = "conventions";

/** Acción de flujo del convenio (`conventions/{id}/{action}/`). */
export const useFlowAction = (id: number, action: string) =>
  useResourceAction(CONV, id, action);

export const useCamposClinicos = (id: number) =>
  useResourceSubList(CONV, id, "campos-clinicos");
export const useParticipantes = (id: number) =>
  useResourceSubList(CONV, id, "participantes");
export const useHistorial = (id: number) => useResourceSubList(CONV, id, "historial");
