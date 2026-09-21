"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";
import { EntityLogo } from "@/components/ui/entity-logo";

/** Logo de la universidad seleccionada en las vistas de internados. */
export function UniversityLogoDisplay({ id }: { id: number }) {
  const { data } = useQuery({
    queryKey: ["universities", id],
    queryFn: () => api.get<WithId>(`/universities/${id}/`).then((r) => r.data),
    staleTime: 10 * 60_000,
    enabled: id > 0,
  });
  const referencia = data ? (data.referencia_logo as string | undefined) ?? null : null;
  return <EntityLogo entidad="universities" id={id} referenciaLogo={referencia} size={56} />;
}
