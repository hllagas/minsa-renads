"use client";

import { useMemo } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { CATALOGO_ENTITY_CONFIGS } from "@/lib/catalogos/entities";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { hasAnnexes, hasLogo } from "@/lib/api/storage";
import type { RowAction } from "@/lib/crud/types";
import type { WithId } from "@/lib/api/query";
import { api, type Paginated } from "@/lib/api/client";
import { ResourceCrud } from "@/components/crud/resource-crud";
import { IpressSedeDocenteAction } from "@/components/catalogos/ipress-sede-docente-action";
import { LogoUploadAction } from "@/components/catalogos/logo-upload-dialog";
import { AnnexChecklistAction } from "@/components/almacenamiento/annex-checklist-dialog";
import { EntityLogo } from "@/components/ui/entity-logo";
import { Button } from "@/components/ui/button";

/** CRUD de una entidad organizacional/académica, resuelta por el slug de la ruta. */
export default function EntidadCatalogoPage() {
  const params = useParams<{ entidad: string }>();
  const config = CATALOGO_ENTITY_CONFIGS[params.entidad];
  const user = useAuthStore((s) => s.user);
  const entidad = params.entidad;

  // Niveles académicos — solo se usa para calcular el filtro inicial de "Pregrado".
  const isProfessionalCareers = entidad === "professional-careers";
  const levelsQuery = useQuery({
    queryKey: ["academic-levels", "for-default-filter"],
    queryFn: () =>
      api
        .get<Paginated<WithId>>("/academic-levels/")
        .then((r) => r.data.results),
    enabled: isProfessionalCareers,
    staleTime: 10 * 60_000,
  });

  // ID del nivel "Pregrado" (filtro default para carreras profesionales).
  const initialFilters = useMemo<Record<string, string> | undefined>(() => {
    if (!isProfessionalCareers || !levelsQuery.data) return undefined;
    const pregrado = levelsQuery.data.find((l) =>
      String(l.nombre ?? "").toLowerCase().includes("pregrado"),
    );
    return pregrado ? { nivel_academico: String(pregrado.id) } : undefined;
  }, [isProfessionalCareers, levelsQuery.data]);

  if (!config) {
    return (
      <div className="grid gap-3">
        <p className="text-sm text-muted-foreground">Entidad no encontrada.</p>
        <Button
          variant="outline"
          render={<Link href="/catalogos">Volver a catálogos</Link>}
        />
      </div>
    );
  }

  const isUniversities = entidad === "universities";
  const actions: RowAction<WithId>[] = [];

  // Logo (subir/reemplazar) — 5 entidades con logo, solo `Administrador RENADS`.
  // Universidades queda excluida: su logo se gestiona **dentro del formulario** de edición
  // (ver `renderEditInfo` en la config) y su listado se muestra en tarjetas con el logo.
  if (hasLogo(entidad) && !isUniversities && userHasRole(user, "Administrador RENADS")) {
    actions.push({
      key: "logo",
      label: "Logo",
      render: (row) => <LogoUploadAction entidad={entidad} row={row} />,
      onClick: () => {},
    });
  }

  // Anexos (declaraciones juradas por actor) — solo `Administrador RENADS` en /catalogos.
  if (hasAnnexes(entidad) && userHasRole(user, "Administrador RENADS")) {
    actions.push({
      key: "anexos",
      label: "Anexos",
      render: (row) => <AnnexChecklistAction entidad={entidad} row={row} />,
      onClick: () => {},
    });
  }

  // La acción «sede docente» vive solo en /catalogos/entidades/ipress y solo para CONAPRES.
  if (entidad === "ipress" && userHasRole(user, "CONAPRES")) {
    actions.push({
      key: "sede-docente",
      label: "Sede docente",
      render: (row) => <IpressSedeDocenteAction row={row} />,
      onClick: () => {},
    });
  }

  const rowActions = actions.length ? actions : undefined;

  return (
    <div>
      <div className="mb-4">
        <Link
          href="/catalogos"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Catálogos
        </Link>
      </div>
      <ResourceCrud
        config={config}
        rowActions={rowActions}
        initialFilters={initialFilters}
        cardView={isUniversities}
        renderCard={
          isUniversities
            ? (row: WithId) => (
                <div className="flex flex-col items-center gap-3 text-center">
                  <EntityLogo
                    entidad="universities"
                    id={row.id}
                    referenciaLogo={(row.referencia_logo as string | undefined) ?? null}
                    size={80}
                  />
                  <div className="grid gap-0.5">
                    <p className="text-sm leading-tight font-medium">
                      {String(row.nombre ?? "—")}
                    </p>
                    {row.siglas ? (
                      <p className="text-xs text-muted-foreground">
                        {String(row.siglas)}
                      </p>
                    ) : null}
                  </div>
                </div>
              )
            : undefined
        }
      />
    </div>
  );
}
