"use client";

import { isSuperuser, useAuthStore } from "@/lib/auth/store";

/** Alcance de universidad del usuario (derivado de `perfiles`, `tipo_entidad === "university"`). */
export interface UniversityScope {
  /** Ids de universidades a las que el usuario tiene acceso (vacío = sin restricción). */
  ids: number[];
  /** Si el usuario está restringido a exactamente una universidad, su id; si no, `null`. */
  singleId: number | null;
  /** `true` si el usuario está acotado a una o más universidades concretas. */
  scoped: boolean;
}

const NO_SCOPE: UniversityScope = { ids: [], singleId: null, scoped: false };

/**
 * Deriva el alcance institucional de universidad del usuario autenticado.
 * Superusuario/`Administrador RENADS` (sin perfil de universidad) → sin restricción (`scoped=false`).
 * Un usuario con un único perfil `university` → `singleId` para autocompletar y ocultar el selector
 * (UX: no pedir lo que ya se conoce). El backend sigue siendo la autoridad final del alcance.
 */
export function useUniversityScope(): UniversityScope {
  const user = useAuthStore((s) => s.user);
  if (!user || isSuperuser(user)) return NO_SCOPE;

  const ids = Array.from(
    new Set(
      user.perfiles
        .filter((p) => p.tipo_entidad === "university")
        .map((p) => p.id_objeto),
    ),
  );
  if (ids.length === 0) return NO_SCOPE;
  return { ids, singleId: ids.length === 1 ? ids[0] : null, scoped: true };
}
