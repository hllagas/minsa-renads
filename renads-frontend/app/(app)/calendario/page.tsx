"use client";

import { calendarActivitiesConfig } from "@/lib/calendario/activities";
import { ResourceCrud } from "@/components/crud/resource-crud";

/**
 * Calendario administrativo — CRUD de actividades del proyecto RENADS.
 * Escritura solo `Administrador RENADS` (backend `IsAdminRoleOrReadOnly`). Las actividades
 * con `controla_acceso` gobiernan la ventana de escritura de los módulos asociados.
 */
export default function CalendarioPage() {
  return <ResourceCrud config={calendarActivitiesConfig} />;
}
