"use client";

import { useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle } from "lucide-react";

import { CATALOGO_ENTITY_CONFIGS } from "@/lib/catalogos/entities";
import type { ResourceConfig } from "@/lib/crud/types";
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
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

/** Lee `nombre` de un objeto `*_detalle` de FK (o «—»). */
const det = (v: unknown): string =>
  v && typeof v === "object" && "nombre" in v
    ? String((v as { nombre?: unknown }).nombre ?? "—")
    : "—";

/** Etiqueta combinada del `ubigeo_detalle`. */
const ubigeoLabel = (v: unknown): string => {
  if (!v || typeof v !== "object") return "—";
  const u = v as Record<string, unknown>;
  return [u.departamento, u.provincia, u.distrito].filter(Boolean).join(" › ") || "—";
};

/** Fila de detalle: etiqueta + valor. */
function DetailRow({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="grid gap-0.5">
      <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className="text-sm text-foreground">{value || "—"}</span>
    </div>
  );
}

/** Dialog de detalle completo de una universidad. */
function UniversityDetailDialog({
  row,
  onClose,
}: {
  row: WithId | null;
  onClose: () => void;
}) {
  if (!row) return null;
  const r = row as Record<string, unknown>;
  return (
    <Dialog open={!!row} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="sr-only">Detalle de universidad</DialogTitle>
        </DialogHeader>

        {/* Logo + nombre */}
        <div className="flex flex-col items-center gap-3 pb-4 text-center">
          <EntityLogo
            entidad="universities"
            id={row.id}
            referenciaLogo={(r.referencia_logo as string | undefined) ?? null}
            size={88}
          />
          <div>
            <p className="text-base font-semibold leading-tight">
              {String(r.nombre ?? "—")}
            </p>
            {r.siglas ? (
              <p className="mt-0.5 text-sm text-muted-foreground">{String(r.siglas)}</p>
            ) : null}
          </div>
          <Badge variant={r.activo ? "default" : "secondary"} className="gap-1">
            {r.activo ? (
              <CheckCircle2 className="size-3" />
            ) : (
              <XCircle className="size-3" />
            )}
            {r.activo ? "Activa" : "Inactiva"}
          </Badge>
        </div>

        <div className="divide-y">
          {/* Clasificación */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-3 py-4">
            <DetailRow label="Tipo de gestión"    value={det(r.tipo_gestion_detalle)} />
            <DetailRow label="Tipo de entidad"    value={det(r.tipo_entidad_detalle)} />
            <DetailRow label="Tipo de autorización" value={det(r.tipo_autorizacion_detalle)} />
            <DetailRow label="Código INEI"        value={r.codigo_inei as string} />
          </div>

          {/* Resolución y vigencia */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-3 py-4">
            <DetailRow label="N° resolución"      value={r.numero_resolucion as string} />
            <DetailRow label="Fecha constitución" value={r.fecha_constitucion as string} />
            <DetailRow label="Fecha autorización" value={r.fecha_autorizacion as string} />
          </div>

          {/* Contacto y ubicación */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-3 py-4">
            <DetailRow label="Dirección legal"    value={r.direccion_legal as string} />
            <DetailRow label="Teléfono"           value={r.telefono as string} />
            <DetailRow label="Correo institucional" value={r.correo_institucional as string} />
            <DetailRow label="Ubigeo"             value={ubigeoLabel(r.ubigeo_detalle)} />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** CRUD de una entidad organizacional/académica, resuelta por el slug de la ruta. */
export default function EntidadCatalogoPage() {
  const params = useParams<{ entidad: string }>();
  const baseConfig = CATALOGO_ENTITY_CONFIGS[params.entidad];
  const user = useAuthStore((s) => s.user);
  const entidad = params.entidad;

  // Estado del detalle de universidad (antes del guard para respetar reglas de hooks).
  const [detailRow, setDetailRow] = useState<WithId | null>(null);

  const config: ResourceConfig | undefined = baseConfig;

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
                  {/* Logo + nombre: clickeable para ver el detalle */}
                  <button
                    type="button"
                    className="flex flex-col items-center gap-2 rounded-md p-1 transition-opacity hover:opacity-75 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    onClick={() => setDetailRow(row)}
                    aria-label={`Ver detalle de ${String(row.nombre ?? "universidad")}`}
                  >
                    <EntityLogo
                      entidad="universities"
                      id={row.id}
                      referenciaLogo={(row.referencia_logo as string | undefined) ?? null}
                      size={80}
                    />
                    <div className="grid gap-0.5">
                      <p className="text-sm leading-tight font-medium underline-offset-2 hover:underline">
                        {String(row.nombre ?? "—")}
                      </p>
                      {row.siglas ? (
                        <p className="text-xs text-muted-foreground">
                          {String(row.siglas)}
                        </p>
                      ) : null}
                    </div>
                  </button>
                </div>
              )
            : undefined
        }
      />

      {/* Dialog de detalle de universidad */}
      {isUniversities ? (
        <UniversityDetailDialog
          row={detailRow}
          onClose={() => setDetailRow(null)}
        />
      ) : null}
    </div>
  );
}
