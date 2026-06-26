"use client";

import type { components } from "@/lib/api/schema";
import { createResourceHooks } from "@/lib/crud/hooks";

export type ConventionRead = components["schemas"]["ConventionRead"];
export type ConventionWrite = components["schemas"]["ConventionWrite"];

/** Hooks CRUD del recurso `conventions` (lectura = ConventionRead, escritura = ConventionWrite). */
export const conventionHooks = createResourceHooks<ConventionRead, ConventionWrite>(
  "conventions",
);
