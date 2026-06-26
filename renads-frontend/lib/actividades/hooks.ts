"use client";

import type { components } from "@/lib/api/schema";
import { createResourceHooks } from "@/lib/crud/hooks";

export type TeachingActivityRead = components["schemas"]["TeachingActivityRead"];
export type TeachingActivityWrite = components["schemas"]["TeachingActivityWrite"];

/** Hooks CRUD de actividades docente-asistenciales. */
export const teachingActivityHooks = createResourceHooks<
  TeachingActivityRead,
  TeachingActivityWrite
>("teaching-activities");
