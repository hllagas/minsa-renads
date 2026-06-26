"use client";

import type { components } from "@/lib/api/schema";
import { createResourceHooks } from "@/lib/crud/hooks";

export type InternshipRead = components["schemas"]["InternshipRead"];
export type InternshipWrite = components["schemas"]["InternshipWrite"];
export type RotationRead = components["schemas"]["RotationRead"];

/** Hooks CRUD de internados (read = InternshipRead, write = InternshipWrite). */
export const internshipHooks = createResourceHooks<InternshipRead, InternshipWrite>(
  "internships",
);

/** Hooks de lectura de rotaciones (la escritura va por acciones de flujo). */
export const rotationHooks = createResourceHooks<RotationRead, Record<string, unknown>>(
  "rotations",
);
