"use client";

import { useMemo, useState } from "react";
import { toast } from "sonner";

import { api } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";
import { extractApiError } from "@/lib/api/errors";
import { createResourceHooks } from "@/lib/crud/hooks";
import { useUniversityScope } from "@/lib/auth/scope";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { TUTOR_FIELDS } from "@/lib/internados/persons";
import { docCodigoById, docLengthByCodigo } from "@/lib/validation/doc-number";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { Input } from "@/components/ui/input";
import { ResourceForm } from "@/components/crud/resource-form";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Search } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { Paginated } from "@/lib/api/client";

type Step =
  | { kind: "step1" }
  | { kind: "searching" }
  | { kind: "new" }                       // tutor no encontrado — crear
  | { kind: "found"; tutor: WithId };     // tutor encontrado — asignar universidad

const tutorHooks = createResourceHooks<WithId, Record<string, unknown>>("tutors");

interface Props {
  /** Universidad actual del contexto (para defaultear el form y la asignación). */
  universidad: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Callback tras crear o asignar universidad con éxito. */
  onSuccess?: () => void;
}

export function TutorCreateWizard({ universidad, open, onOpenChange, onSuccess }: Props) {
  const user = useAuthStore((s) => s.user);
  const isAdmin = userHasRole(user, "Administrador RENADS");
  const { ids: idsAmbito } = useUniversityScope();

  const [step, setStep] = useState<Step>({ kind: "step1" });
  const [tipoDoc, setTipoDoc] = useState<number | null>(null);
  const [numDoc, setNumDoc] = useState("");

  const createM = tutorHooks.useCreate();
  const updateM = tutorHooks.useUpdate();

  function reset() {
    setStep({ kind: "step1" });
    setTipoDoc(null);
    setNumDoc("");
  }

  function handleOpenChange(v: boolean) {
    if (!v) reset();
    onOpenChange(v);
  }

  async function handleBuscar() {
    if (!tipoDoc || !numDoc.trim()) {
      toast.error("Ingresa el tipo y número de documento.");
      return;
    }
    setStep({ kind: "searching" });
    try {
      const { data } = await api.get<WithId>("/tutors/buscar/", {
        params: { tipo_documento_identidad: tipoDoc, numero_documento: numDoc.trim() },
      });
      setStep({ kind: "found", tutor: data });
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status;
      if (status === 404) {
        setStep({ kind: "new" });
      } else {
        toast.error(extractApiError(e));
        setStep({ kind: "step1" });
      }
    }
  }

  function handleCreate(payload: Record<string, unknown>) {
    createM.mutate(
      { ...payload, universidades: [universidad] },
      {
        onSuccess: () => {
          toast.success("Tutor creado.");
          handleOpenChange(false);
          onSuccess?.();
        },
        onError: (e) => toast.error(extractApiError(e)),
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {step.kind === "found" ? "Tutor encontrado" : "Nuevo tutor"}
          </DialogTitle>
        </DialogHeader>

        {/* Paso 1 — Búsqueda por documento */}
        {(step.kind === "step1" || step.kind === "searching") && (
          <Step1
            tipoDoc={tipoDoc}
            numDoc={numDoc}
            onTipoDoc={setTipoDoc}
            onNumDoc={setNumDoc}
            onBuscar={handleBuscar}
            loading={step.kind === "searching"}
          />
        )}

        {/* Paso 2a — No encontrado: form completo de alta */}
        {step.kind === "new" && (
          <Step2New
            tipoDocDefault={tipoDoc}
            numDocDefault={numDoc}
            universidadDefault={universidad}
            isAdmin={isAdmin}
            submitting={createM.isPending}
            onBack={() => setStep({ kind: "step1" })}
            onSubmit={handleCreate}
          />
        )}

        {/* Paso 2b — Encontrado: asignación de universidad */}
        {step.kind === "found" && (
          <Step2Found
            tutor={step.tutor}
            universidad={universidad}
            idsAmbito={idsAmbito}
            isAdmin={isAdmin}
            submitting={updateM.isPending}
            onBack={() => setStep({ kind: "step1" })}
            onCancel={() => handleOpenChange(false)}
            onSubmit={(universidades) =>
              updateM.mutate(
                { id: step.tutor.id as number, payload: { universidades } },
                {
                  onSuccess: () => {
                    toast.success("Universidades del tutor actualizadas.");
                    handleOpenChange(false);
                    onSuccess?.();
                  },
                  onError: (e) => toast.error(extractApiError(e)),
                },
              )
            }
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------

function Step1({
  tipoDoc,
  numDoc,
  onTipoDoc,
  onNumDoc,
  onBuscar,
  loading,
}: {
  tipoDoc: number | null;
  numDoc: string;
  onTipoDoc: (v: number | null) => void;
  onNumDoc: (v: string) => void;
  onBuscar: () => void;
  loading: boolean;
}) {
  // Catálogo de tipos de documento para resolver codigo → longitud esperada.
  const docTypesQuery = useQuery({
    queryKey: ["identity-document-types"],
    queryFn: () =>
      api
        .get<Paginated<WithId>>("/identity-document-types/")
        .then((r) => r.data.results),
    staleTime: 30 * 60_000,
  });

  const docCodigo = docCodigoById(docTypesQuery.data, tipoDoc);
  const maxLen = tipoDoc != null ? docLengthByCodigo(docCodigo) : 9;

  function handleNumDoc(raw: string) {
    // Solo dígitos, truncado al máximo del tipo seleccionado.
    const digits = raw.replace(/\D/g, "").slice(0, maxLen);
    onNumDoc(digits);
  }

  return (
    <div className="grid gap-4">
      <p className="text-sm text-muted-foreground">
        Ingresa el documento para verificar si el tutor ya existe en el sistema.
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="grid gap-1.5">
          <Label className="text-sm">Tipo de documento</Label>
          <EntityCombobox
            endpoint="identity-document-types"
            value={tipoDoc}
            onChange={(v) => {
              onTipoDoc(v);
              // Limpiar número al cambiar tipo para evitar longitud incorrecta.
              onNumDoc("");
            }}
            placeholder="Seleccionar tipo…"
          />
        </div>
        <div className="grid gap-1.5">
          <Label className="text-sm">Número de documento</Label>
          <Input
            value={numDoc}
            onChange={(e) => handleNumDoc(e.target.value)}
            placeholder={tipoDoc != null ? `${maxLen} dígitos` : "Número de documento"}
            maxLength={maxLen}
            inputMode="numeric"
            pattern="[0-9]*"
            onKeyDown={(e) => e.key === "Enter" && onBuscar()}
          />
          {tipoDoc != null && numDoc.length > 0 && numDoc.length < maxLen && (
            <p className="text-xs text-muted-foreground">
              {numDoc.length}/{maxLen} dígitos
            </p>
          )}
        </div>
      </div>
      <div className="flex justify-end">
        <Button
          onClick={onBuscar}
          disabled={loading || !tipoDoc || numDoc.length !== maxLen}
        >
          {loading ? "Buscando…" : "Buscar tutor"}
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

function Step2New({
  tipoDocDefault,
  numDocDefault,
  universidadDefault,
  isAdmin,
  submitting,
  onBack,
  onSubmit,
}: {
  tipoDocDefault: number | null;
  numDocDefault: string;
  universidadDefault: number;
  isAdmin: boolean;
  submitting: boolean;
  onBack: () => void;
  onSubmit: (payload: Record<string, unknown>) => void;
}) {
  const initial = useMemo<Record<string, unknown>>(() => {
    const v: Record<string, unknown> = {
      activo: true,
      // Precargar tipo y número buscados
      ...(tipoDocDefault != null ? { tipo_documento_identidad: tipoDocDefault } : {}),
      ...(numDocDefault ? { numero_documento: numDocDefault } : {}),
      // Para admin: no fijar universidades en initial (puede elegir varias).
      // Para usuario Universidad: se inyectan al submit.
      ...(isAdmin ? {} : { universidades: [universidadDefault] }),
    };
    return v;
  }, [tipoDocDefault, numDocDefault, universidadDefault, isAdmin]);

  // Admins ven el campo multiselect de universidades; usuarios scoped lo ocultan (se fija al submit).
  const fields = useMemo(
    () =>
      isAdmin
        ? TUTOR_FIELDS
        : TUTOR_FIELDS.filter((f) => f.name !== "universidades" && f.name !== "_s3_univ"),
    [isAdmin],
  );

  return (
    <div className="grid gap-3">
      <div className="flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
        <span>Tutor no encontrado. Completa los datos para registrarlo.</span>
      </div>
      <ResourceForm
        fields={fields}
        initial={initial}
        submitting={submitting}
        onCancel={onBack}
        onSubmit={onSubmit}
        formClassName="grid max-h-[60vh] grid-cols-1 gap-x-5 gap-y-2 overflow-x-hidden overflow-y-auto px-1 py-1 sm:grid-cols-2"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------

type UnivInfo = { id: number; nombre: string; siglas: string };
type UnivRow = UnivInfo & { editable: boolean };

function Step2Found({
  tutor,
  universidad,
  idsAmbito,
  isAdmin,
  submitting,
  onBack,
  onCancel,
  onSubmit,
}: {
  tutor: WithId;
  universidad: number;
  idsAmbito: number[];
  isAdmin: boolean;
  submitting: boolean;
  onBack: () => void;
  onCancel: () => void;
  onSubmit: (universidades: number[]) => void;
}) {
  // Lista de universidades actuales del tutor (viene de universidades_detalle del serializer).
  const universidadesDetalle = Array.isArray(tutor.universidades_detalle)
    ? (tutor.universidades_detalle as UnivInfo[])
    : [];

  // Normalize IDs to numbers. Fallback a universidades[] plano si _detalle no viene del endpoint buscar/.
  const currentIds = useMemo(() => {
    if (universidadesDetalle.length > 0) {
      return new Set(universidadesDetalle.map((u) => Number(u.id)));
    }
    const plain = Array.isArray(tutor.universidades) ? (tutor.universidades as unknown[]) : [];
    return new Set(plain.map(Number));
  }, [universidadesDetalle, tutor.universidades]);

  // Admin: carga TODAS las universidades. El backend limita page_size (cap DRF), así que
  // paginamos siguiendo `next` hasta agotar la lista completa.
  const todasQuery = useQuery({
    queryKey: ["universities", "all-for-wizard"],
    queryFn: async () => {
      const all: WithId[] = [];
      let page = 1;
      // Cota de seguridad: 20 páginas máx (evita loop infinito ante backend mal formado).
      for (let guard = 0; guard < 20; guard++) {
        const { data } = await api.get<Paginated<WithId>>("/universities/", {
          params: { page: String(page), page_size: "100", ordering: "nombre" },
        });
        all.push(...data.results);
        if (!data.next) break;
        page += 1;
      }
      return all;
    },
    staleTime: 10 * 60_000,
    enabled: isAdmin,
  });
  const todasUniversidades = useMemo(() => todasQuery.data ?? [], [todasQuery.data]);

  // Scoped: consulta el API por cada ID del ámbito para obtener nombre/siglas reales.
  // Filtra automáticamente perfiles huérfanos (ID no existe en la tabla → fetch falla → se omite).
  const ambitoQuery = useQuery({
    queryKey: ["universities", "ambito", idsAmbito],
    queryFn: async () => {
      const results = await Promise.all(
        idsAmbito.map((id) =>
          api
            .get<WithId>(`/universities/${id}/`)
            .then((r) => ({
              id: Number(r.data.id),
              nombre: String(r.data.nombre ?? ""),
              siglas: String(r.data.siglas ?? ""),
            }))
            .catch(() => null),
        ),
      );
      return results.filter((u): u is UnivInfo => u !== null);
    },
    staleTime: 10 * 60_000,
    enabled: !isAdmin && idsAmbito.length > 0,
  });
  // Solo universidades del ámbito que realmente existen en el API.
  const univsAmbito = useMemo(() => ambitoQuery.data ?? [], [ambitoQuery.data]);
  const univsAmbitoLoading = !isAdmin && ambitoQuery.isLoading;

  const [selectedIds, setSelectedIds] = useState<Set<number>>(() => new Set(currentIds));

  function toggleId(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  // IDs editables: admin → todos; scoped → solo IDs que realmente existen en el API.
  const editableIds = isAdmin
    ? new Set(todasUniversidades.map((u) => Number(u.id)))
    : new Set(univsAmbito.map((u) => u.id));

  // Búsqueda y paginación (cliente).
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 10;

  const isLoading = isAdmin ? todasQuery.isLoading : univsAmbitoLoading;

  const displayList = useMemo<UnivRow[]>(() => {
    // Asignadas primero, luego alfabético.
    const sortFn = (a: UnivRow, b: UnivRow) => {
      const aA = currentIds.has(a.id) ? 0 : 1;
      const bA = currentIds.has(b.id) ? 0 : 1;
      if (aA !== bA) return aA - bA;
      return a.nombre.localeCompare(b.nombre, "es");
    };
    if (isAdmin) {
      return todasUniversidades
        .map((u) => ({
          id: Number(u.id),
          nombre: String(u.nombre || u.id),
          siglas: u.siglas ? String(u.siglas) : "",
          editable: true,
        }))
        .sort(sortFn);
    }
    const editable: UnivRow[] = univsAmbito
      .map((u) => ({ ...u, editable: true }))
      .sort(sortFn);
    const readOnly: UnivRow[] = universidadesDetalle
      .filter((u) => !editableIds.has(u.id))
      .map((u) => ({ ...u, editable: false }));
    return [...editable, ...readOnly];
  }, [isAdmin, todasUniversidades, univsAmbito, universidadesDetalle, editableIds, currentIds]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return displayList;
    return displayList.filter(
      (u) => u.nombre.toLowerCase().includes(q) || u.siglas.toLowerCase().includes(q),
    );
  }, [displayList, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  function handleSearch(q: string) {
    setSearch(q);
    setPage(1);
  }

  const apellidoNombres = [tutor.apellido_paterno, tutor.apellido_materno, tutor.nombres]
    .map((x) => String(x ?? "").trim())
    .filter(Boolean)
    .join(" ");

  const tipoDetalle = tutor.tipo_documento_identidad_detalle as { codigo?: string } | undefined;
  const profesionDetalle = tutor.profesion_detalle as { nombre?: string } | undefined;

  function handleSubmit() {
    // Lista final: actuales fuera del ámbito editable (se conservan) + seleccionados del ámbito.
    const noEditablesActuales = [...currentIds].filter((id) => !editableIds.has(id));
    const editablesSeleccionados = [...selectedIds].filter((id) => editableIds.has(id));
    const final = [...new Set([...noEditablesActuales, ...editablesSeleccionados])];
    onSubmit(final);
  }

  return (
    <div className="grid gap-4">
      <div className="flex items-center gap-2 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200">
        <span>Tutor encontrado en el sistema. Revisa las universidades asignadas.</span>
      </div>

      {/* Info del tutor */}
      <div className="rounded-md border bg-muted/30 p-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
        <div className="col-span-2 font-medium">{apellidoNombres || "—"}</div>
        <div className="text-muted-foreground">Documento</div>
        <div>{tipoDetalle?.codigo ?? "—"} · {String(tutor.numero_documento ?? "—")}</div>
        <div className="text-muted-foreground">Profesión</div>
        <div>{profesionDetalle?.nombre ?? "—"}</div>
        <div className="text-muted-foreground">Colegiatura</div>
        <div>{String(tutor.numero_colegiatura ?? "—")}</div>
      </div>

      <hr className="border-border" />

      {/* Selector de universidades */}
      <div className="grid gap-2">
        <Label className="text-sm font-medium">Universidades asignadas</Label>

        {/* Búsqueda */}
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por nombre o abreviatura…"
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="h-9 pl-8"
          />
        </div>

        {/* Lista de universidades como cajas seleccionables */}
        {isLoading ? (
          <p className="py-4 text-center text-xs text-muted-foreground">Cargando universidades…</p>
        ) : (
          <>
            {paginated.length === 0 ? (
              <div className="rounded-md border border-dashed px-3 py-8 text-center text-sm text-muted-foreground">
                {search ? `Sin resultados para "${search}".` : "Sin universidades disponibles."}
              </div>
            ) : (
              <div className="grid gap-1.5">
                {paginated.map((u) => {
                  const checked = selectedIds.has(u.id);
                  return (
                    <label
                      key={u.id}
                      htmlFor={`univ-box-${u.id}`}
                      className={`flex items-center gap-3 rounded-md border px-3 py-2.5 transition-colors ${
                        u.editable
                          ? "cursor-pointer hover:border-primary/40 hover:bg-muted/40"
                          : "cursor-not-allowed opacity-60"
                      } ${checked ? "border-primary bg-primary/5" : "border-input"}`}
                    >
                      <Checkbox
                        id={`univ-box-${u.id}`}
                        checked={checked}
                        disabled={!u.editable}
                        onCheckedChange={() => u.editable && toggleId(u.id)}
                        className="shrink-0"
                      />
                      <span className="flex min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-0.5 text-sm font-medium leading-tight">
                        <span className="min-w-0">{u.nombre}</span>
                        {u.siglas && (
                          <span className="font-normal text-muted-foreground">({u.siglas})</span>
                        )}
                        {!u.editable && (
                          <Badge variant="outline" className="text-xs">
                            Otra univ.
                          </Badge>
                        )}
                      </span>
                    </label>
                  );
                })}
              </div>
            )}

            {/* Paginación + conteo */}
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>
                {selectedIds.size > 0 && (
                  <span className="font-medium text-foreground">
                    {selectedIds.size} seleccionada{selectedIds.size !== 1 ? "s" : ""}{" · "}
                  </span>
                )}
                {filtered.length} {filtered.length === 1 ? "universidad" : "universidades"}
                {search ? ` · "${search}"` : ""}
              </span>
              {totalPages > 1 && (
                <div className="flex items-center gap-2">
                  <span>Pág. {page} / {totalPages}</span>
                  <div className="flex gap-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-7 px-2 text-xs"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      ←
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-7 px-2 text-xs"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                    >
                      →
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      <div className="flex justify-between gap-2">
        <Button variant="outline" onClick={onBack} disabled={submitting}>
          ← Volver
        </Button>
        <div className="flex gap-2">
          {selectedIds.size === 0 && (
            <Button variant="ghost" onClick={onCancel} disabled={submitting}>
              Cancelar
            </Button>
          )}
          <Button onClick={handleSubmit} disabled={submitting || selectedIds.size === 0}>
            {submitting ? "Guardando…" : "Guardar asignación"}
          </Button>
        </div>
      </div>
    </div>
  );
}
