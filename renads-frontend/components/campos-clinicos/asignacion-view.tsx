"use client";

import React, { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Pencil, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import type { WithId } from "@/lib/api/query";
import { api, type Paginated } from "@/lib/api/client";
import { createResourceHooks } from "@/lib/crud/hooks";
import { resourceKeys } from "@/lib/api/query";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { extractApiError } from "@/lib/api/errors";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EntityCombobox } from "@/components/form/entity-combobox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ClinicalAllocationsBulkUploadDialog } from "@/components/campos-clinicos/clinical-allocations-bulk-upload-dialog";
import { NuevaAsignacionDialog } from "@/components/campos-clinicos/nueva-asignacion-dialog";
import { EditarAsignacionDialog } from "@/components/campos-clinicos/editar-asignacion-dialog";

// ─── tipos ────────────────────────────────────────────────────────────────────

interface IpressDetalle {
  id: number | string;
  nombre: string;
  codigo_renipress?: string;
  unidad_ejecutora?: { id: number | string; nombre: string } | null;
  ambito_geografico_sanitario?: { id: number; nombre: string } | null;
}

interface ColDef {
  key: string;
  label: string;
}

interface CeldaData {
  autorizados: number;
  rowId: number;
}

interface UnivRow {
  univKey: string;
  univNombre: string;
  celdas: Map<string, CeldaData>;
  totAutorizados: number;
}

interface SedeGroup {
  ipressKey: string;
  ipressNombre: string;
  universidades: UnivRow[];
  totAutorizados: number;
}

interface ConvenioGroup {
  convenioKey: string;
  convenioLabel: string;
  sedes: SedeGroup[];
  totAutorizados: number;
}

interface UEGroup {
  ueKey: string;
  ueNombre: string;
  convenios: ConvenioGroup[];
  totAutorizados: number;
}

interface AmbitoGroup {
  ambitoKey: string;
  ambitoNombre: string;
  ues: UEGroup[];
  totAutorizados: number;
}

interface MatrixData {
  columns: ColDef[];
  ambitos: AmbitoGroup[];
}

// ─── helpers ──────────────────────────────────────────────────────────────────

function getColKey(row: WithId, esPregrado: boolean): string {
  if (esPregrado) {
    const cp = row.carrera_profesional_detalle as WithId | null;
    return `cp-${cp?.id ?? "?"}`;
  }
  const esp = row.especialidad_detalle as WithId | null;
  return `esp-${esp?.id ?? "?"}`;
}

function getColLabel(row: WithId, esPregrado: boolean): string {
  if (esPregrado) {
    const cp = row.carrera_profesional_detalle as WithId | null;
    return String(cp?.nombre ?? "—");
  }
  const esp = row.especialidad_detalle as WithId | null;
  return String(esp?.nombre ?? "—");
}

function buildMatrix(rows: WithId[], esPregrado: boolean): MatrixData {
  const colMap = new Map<string, string>();
  const ambitoMap = new Map<
    string,
    {
      nombre: string;
      ues: Map<
        string,
        {
          nombre: string;
          convenios: Map<
            string,
            {
              label: string;
              sedes: Map<string, { nombre: string; univs: Map<string, UnivRow> }>;
            }
          >;
        }
      >;
    }
  >();

  for (const row of rows) {
    const ip = (row.ipress_detalle ?? {}) as IpressDetalle;
    const ags = ip.ambito_geografico_sanitario;
    const ue = ip.unidad_ejecutora;
    const convenioD = row.convenio_detalle as Record<string, unknown> | null;
    const univD = row.universidad_detalle as Record<string, unknown> | null;

    const ambitoKey = ags ? `${ags.id}` : "sin-ambito";
    const ambitoNombre = ags?.nombre ?? "Sin ámbito";
    const ueKey = ue ? `${ue.id}` : "sin-ue";
    const ueNombre = ue?.nombre ?? "Sin unidad ejecutora";
    const convenioKey = `${row.convenio ?? "?"}`;
    const convLabel = String(
      convenioD?.nomenclatura ?? convenioD?.titulo ?? "Sin convenio",
    );
    const ipressKey = `${ip.id ?? row.ipress ?? "?"}`;
    const ipressNombre = ip.nombre ?? "—";
    const univKey = `${row.universidad ?? "?"}`;
    const univNombre = String(univD?.nombre ?? "Sin universidad");

    const colKey = getColKey(row, esPregrado);
    const colLabel = getColLabel(row, esPregrado);
    colMap.set(colKey, colLabel);

    // Ámbito
    if (!ambitoMap.has(ambitoKey)) {
      ambitoMap.set(ambitoKey, { nombre: ambitoNombre, ues: new Map() });
    }
    const ambitoEntry = ambitoMap.get(ambitoKey)!;

    // UE
    if (!ambitoEntry.ues.has(ueKey)) {
      ambitoEntry.ues.set(ueKey, { nombre: ueNombre, convenios: new Map() });
    }
    const ueEntry = ambitoEntry.ues.get(ueKey)!;

    // Convenio
    if (!ueEntry.convenios.has(convenioKey)) {
      ueEntry.convenios.set(convenioKey, { label: convLabel, sedes: new Map() });
    }
    const convenioEntry = ueEntry.convenios.get(convenioKey)!;

    // Sede
    if (!convenioEntry.sedes.has(ipressKey)) {
      convenioEntry.sedes.set(ipressKey, {
        nombre: ipressNombre,
        univs: new Map(),
      });
    }
    const sedeEntry = convenioEntry.sedes.get(ipressKey)!;

    // Universidad (hoja)
    if (!sedeEntry.univs.has(univKey)) {
      sedeEntry.univs.set(univKey, {
        univKey,
        univNombre,
        celdas: new Map(),
        totAutorizados: 0,
      });
    }
    const univRow = sedeEntry.univs.get(univKey)!;
    const auth = Number(row.campos_clinicos_autorizados) || 0;
    univRow.celdas.set(colKey, { autorizados: auth, rowId: row.id });
    univRow.totAutorizados += auth;
  }

  const columns: ColDef[] = Array.from(colMap.entries())
    .map(([key, label]) => ({ key, label }))
    .sort((a, b) => a.label.localeCompare(b.label, "es"));

  const ambitos: AmbitoGroup[] = Array.from(ambitoMap.entries())
    .map(([ambitoKey, aEntry]) => {
      const ues: UEGroup[] = Array.from(aEntry.ues.entries())
        .map(([ueKey, ueEntry]) => {
          const convenios: ConvenioGroup[] = Array.from(
            ueEntry.convenios.entries(),
          )
            .map(([convenioKey, cEntry]) => {
              const sedes: SedeGroup[] = Array.from(cEntry.sedes.entries())
                .map(([ipressKey, sEntry]) => {
                  const universidades: UnivRow[] = Array.from(
                    sEntry.univs.values(),
                  ).sort((a, b) =>
                    a.univNombre.localeCompare(b.univNombre, "es"),
                  );
                  return {
                    ipressKey,
                    ipressNombre: sEntry.nombre,
                    universidades,
                    totAutorizados: universidades.reduce(
                      (s, u) => s + u.totAutorizados,
                      0,
                    ),
                  };
                })
                .sort((a, b) =>
                  a.ipressNombre.localeCompare(b.ipressNombre, "es"),
                );
              return {
                convenioKey,
                convenioLabel: cEntry.label,
                sedes,
                totAutorizados: sedes.reduce(
                  (s, sg) => s + sg.totAutorizados,
                  0,
                ),
              };
            })
            .sort((a, b) =>
              a.convenioLabel.localeCompare(b.convenioLabel, "es"),
            );
          return {
            ueKey,
            ueNombre: ueEntry.nombre,
            convenios,
            totAutorizados: convenios.reduce(
              (s, c) => s + c.totAutorizados,
              0,
            ),
          };
        })
        .sort((a, b) => a.ueNombre.localeCompare(b.ueNombre, "es"));
      return {
        ambitoKey,
        ambitoNombre: aEntry.nombre,
        ues,
        totAutorizados: ues.reduce((s, u) => s + u.totAutorizados, 0),
      };
    })
    .sort((a, b) => a.ambitoNombre.localeCompare(b.ambitoNombre, "es"));

  return { columns, ambitos };
}

// ─── celda de valor ───────────────────────────────────────────────────────────

function CeldaNum({ n }: { n: number }) {
  if (n === 0) return <span className="text-muted-foreground/50">—</span>;
  return <span className="tabular-nums font-medium">{n}</span>;
}

// ─── etiqueta de fila ─────────────────────────────────────────────────────────

function RowLabel({
  label,
  indent,
  expanded,
  onToggle,
  badge,
}: {
  label: string;
  indent: 0 | 1 | 2 | 3 | 4;
  expanded?: boolean;
  onToggle?: () => void;
  badge?: string;
}) {
  const pl =
    indent === 0
      ? ""
      : indent === 1
        ? "pl-4"
        : indent === 2
          ? "pl-8"
          : indent === 3
            ? "pl-12"
            : "pl-16";
  return (
    <span className={`flex items-center gap-1 ${pl}`}>
      {onToggle != null ? (
        <button
          type="button"
          onClick={onToggle}
          className="shrink-0 text-muted-foreground hover:text-foreground"
          aria-label={expanded ? "Contraer" : "Expandir"}
        >
          {expanded ? (
            <ChevronDown className="size-3.5" />
          ) : (
            <ChevronRight className="size-3.5" />
          )}
        </button>
      ) : null}
      <span className="truncate max-w-xs">{label}</span>
      {badge ? (
        <span className="shrink-0 rounded bg-muted px-1 py-0.5 text-[10px] text-muted-foreground">
          {badge}
        </span>
      ) : null}
    </span>
  );
}

// ─── labels de filtros ────────────────────────────────────────────────────────

const ipressLabel = (r: WithId) =>
  [r.codigo_renipress, r.nombre].filter(Boolean).join(" — ") || String(r.id);

// ─── componente principal ─────────────────────────────────────────────────────

export function AsignacionView() {
  const user = useAuthStore((s) => s.user);
  const canWrite = userHasRole(user, "Gobierno Regional", "Administrador RENADS");

  // ── nivel académico
  const nivelesQuery = useQuery({
    queryKey: ["academic-levels", "for-asignaciones"],
    queryFn: () =>
      api
        .get<Paginated<WithId>>("/academic-levels/")
        .then((r) => r.data.results),
    staleTime: 10 * 60_000,
  });
  const niveles = useMemo(() => nivelesQuery.data ?? [], [nivelesQuery.data]);
  const pregradoId = useMemo<number | null>(() => {
    const p = niveles.find((l) =>
      String(l.nombre ?? "").toLowerCase().includes("pregrado"),
    );
    return p ? Number(p.id) : null;
  }, [niveles]);
  const [nivelPicked, setNivelPicked] = useState<number | null>(null);
  const nivel = nivelPicked ?? pregradoId;
  const esPregrado = nivel === pregradoId && pregradoId !== null;

  // ── filtros client-side
  const [filterAmbitoId, setFilterAmbitoId] = useState<number | null>(null);
  const [filterUeId, setFilterUeId] = useState<string | null>(null);
  const [filterIpress, setFilterIpress] = useState<string | null>(null);
  const [filterUnivId, setFilterUnivId] = useState<number | null>(null);
  const [filterCarreraId, setFilterCarreraId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);

  // ── expand state (4 niveles expandibles)
  const [expandedAmbitos, setExpandedAmbitos] = useState<Set<string>>(
    new Set(),
  );
  const [expandedUEs, setExpandedUEs] = useState<Set<string>>(new Set());
  const [expandedConvenios, setExpandedConvenios] = useState<Set<string>>(
    new Set(),
  );
  const [expandedSedes, setExpandedSedes] = useState<Set<string>>(new Set());

  // ── estado de diálogos
  const qc = useQueryClient();
  const [nuevoOpen, setNuevoOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingLeaf, setEditingLeaf] = useState<{
    ipressNombre: string;
    univNombre: string;
    convenioLabel: string;
    rows: WithId[];
  } | null>(null);
  const [deletingLeaf, setDeletingLeaf] = useState<{
    label: string;
    ids: number[];
  } | null>(null);

  // ── data
  const hooks = useMemo(
    () =>
      createResourceHooks<WithId, Record<string, unknown>>(
        "clinical-field-allocations",
      ),
    [],
  );

  const list = hooks.useList({
    ordering: "ipress__nombre,carrera_profesional__nombre",
    filters: {
      ...(nivel
        ? { "carrera_profesional__nivel_academico": String(nivel) }
        : {}),
      page_size: 500,
    },
  });

  const bulkDeleteM = useMutation({
    mutationFn: async (ids: number[]) => {
      const results = await Promise.allSettled(
        ids.map((id) =>
          api.delete(`/clinical-field-allocations/${id}/`),
        ),
      );
      const errors = results.filter(
        (r): r is PromiseRejectedResult => r.status === "rejected",
      );
      return { deleted: ids.length - errors.length, errors };
    },
    onSuccess: ({ deleted, errors }) => {
      qc.invalidateQueries({
        queryKey: resourceKeys.all("clinical-field-allocations"),
      });
      if (deleted > 0) {
        toast.success(
          `${deleted} registro${deleted !== 1 ? "s" : ""} eliminado${deleted !== 1 ? "s" : ""}.`,
        );
        setAutoExpanded(false);
      }
      if (errors.length > 0) {
        toast.error(
          `${errors.length} no se pudo${errors.length !== 1 ? "n" : ""} eliminar.`,
        );
      }
      setDeletingLeaf(null);
    },
    onError: (e) => toast.error(extractApiError(e)),
  });

  // ── filtrado client-side
  const filteredRows = useMemo<WithId[]>(() => {
    let rows = list.data?.results ?? [];
    if (filterAmbitoId) {
      rows = rows.filter((r) => {
        const ip = r.ipress_detalle as IpressDetalle | null;
        return ip?.ambito_geografico_sanitario?.id === filterAmbitoId;
      });
    }
    if (filterUeId) {
      rows = rows.filter((r) => {
        const ip = r.ipress_detalle as IpressDetalle | null;
        return ip?.unidad_ejecutora
          ? String(ip.unidad_ejecutora.id) === filterUeId
          : false;
      });
    }
    if (filterIpress) {
      rows = rows.filter((r) => {
        const ip = r.ipress_detalle as IpressDetalle | null;
        return ip
          ? String(ip.id) === filterIpress ||
              ip.codigo_renipress === filterIpress
          : false;
      });
    }
    if (filterUnivId) {
      rows = rows.filter(
        (r) =>
          r.universidad === filterUnivId ||
          Number(r.universidad) === filterUnivId,
      );
    }
    if (filterCarreraId) {
      rows = rows.filter((r) =>
        esPregrado
          ? Number(r.carrera_profesional) === filterCarreraId
          : Number(r.especialidad) === filterCarreraId,
      );
    }
    if (debouncedSearch.trim()) {
      const q = debouncedSearch.toLowerCase();
      rows = rows.filter((r) => {
        const ip = r.ipress_detalle as IpressDetalle | null;
        const cp = r.carrera_profesional_detalle as WithId | null;
        const esp = r.especialidad_detalle as WithId | null;
        const univ = r.universidad_detalle as WithId | null;
        const conv = r.convenio_detalle as Record<string, unknown> | null;
        return [
          ip?.ambito_geografico_sanitario?.nombre ?? "",
          ip?.unidad_ejecutora?.nombre ?? "",
          ip?.nombre ?? "",
          String(cp?.nombre ?? ""),
          String(esp?.nombre ?? ""),
          String(univ?.nombre ?? ""),
          String(conv?.nomenclatura ?? conv?.titulo ?? ""),
        ]
          .join(" ")
          .toLowerCase()
          .includes(q);
      });
    }
    return rows;
  }, [
    list.data,
    filterAmbitoId,
    filterUeId,
    filterIpress,
    filterUnivId,
    filterCarreraId,
    debouncedSearch,
    esPregrado,
  ]);

  const matrix = useMemo(
    () => buildMatrix(filteredRows, esPregrado),
    [filteredRows, esPregrado],
  );

  // ── auto-expand ámbito y UE al cargar
  const allAmbitoKeys = useMemo(
    () => matrix.ambitos.map((a) => a.ambitoKey),
    [matrix],
  );
  const allUEKeys = useMemo(
    () =>
      matrix.ambitos.flatMap((a) =>
        a.ues.map((u) => `${a.ambitoKey}:${u.ueKey}`),
      ),
    [matrix],
  );
  const [autoExpanded, setAutoExpanded] = useState(false);
  useMemo(() => {
    if (!autoExpanded && allAmbitoKeys.length > 0) {
      setExpandedAmbitos(new Set(allAmbitoKeys));
      setExpandedUEs(new Set(allUEKeys));
      setAutoExpanded(true);
    }
  }, [autoExpanded, allAmbitoKeys, allUEKeys]);

  function toggleAmbito(key: string) {
    setExpandedAmbitos((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }
  function toggleUE(key: string) {
    setExpandedUEs((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }
  function toggleConvenio(key: string) {
    setExpandedConvenios((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }
  function toggleSede(key: string) {
    setExpandedSedes((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  const hasFilters = !!(
    filterAmbitoId ||
    filterUeId ||
    filterIpress ||
    filterUnivId ||
    filterCarreraId ||
    search
  );
  function clearFilters() {
    setFilterAmbitoId(null);
    setFilterUeId(null);
    setFilterIpress(null);
    setFilterUnivId(null);
    setFilterCarreraId(null);
    setSearch("");
  }

  const { columns } = matrix;
  // colSpan total = 1 (descriptor) + columns.length + 1 (total) + (canWrite ? 1 : 0)
  const totalCols = 1 + columns.length + 1 + (canWrite ? 1 : 0);

  // ── helper: extrae registros de una hoja
  function getLeafRows(univ: UnivRow): WithId[] {
    return Array.from(univ.celdas.values())
      .map((c) => list.data?.results?.find((r) => r.id === c.rowId))
      .filter((r): r is WithId => r !== undefined);
  }

  // ── renderizado de fila hoja (Universidad)
  function renderUnivRow(
    univ: UnivRow,
    sede: SedeGroup,
    convenio: ConvenioGroup,
  ) {
    return (
      <TableRow key={`univ-${univ.univKey}`} className="hover:bg-muted/20">
        <TableCell className="py-1.5 text-sm">
          <RowLabel label={univ.univNombre} indent={4} />
        </TableCell>

        {columns.map((col) => {
          const celda = univ.celdas.get(col.key);
          return (
            <TableCell
              key={col.key}
              className="px-2 text-center text-xs"
            >
              <CeldaNum n={celda?.autorizados ?? 0} />
            </TableCell>
          );
        })}

        {/* Total fila */}
        <TableCell className="border-l px-2 text-center text-xs font-semibold">
          <CeldaNum n={univ.totAutorizados} />
        </TableCell>

        {canWrite ? (
          <TableCell className="py-1 pr-2">
            <div className="flex justify-end gap-1">
              <Button
                variant="outline"
                size="icon-sm"
                aria-label="Editar asignaciones"
                title="Editar asignaciones"
                onClick={() => {
                  setEditingLeaf({
                    ipressNombre: sede.ipressNombre,
                    univNombre: univ.univNombre,
                    convenioLabel: convenio.convenioLabel,
                    rows: getLeafRows(univ),
                  });
                  setEditOpen(true);
                }}
              >
                <Pencil />
              </Button>
              <Button
                variant="destructive"
                size="icon-sm"
                aria-label="Eliminar todas las asignaciones"
                title="Eliminar todas"
                onClick={() => {
                  const ids = Array.from(univ.celdas.values()).map(
                    (c) => c.rowId,
                  );
                  setDeletingLeaf({
                    label: `${sede.ipressNombre} / ${univ.univNombre}`,
                    ids,
                  });
                }}
              >
                <Trash2 />
              </Button>
            </div>
          </TableCell>
        ) : null}
      </TableRow>
    );
  }

  // ── renderizado de fila sede
  function renderSedeRow(
    sede: SedeGroup,
    convenio: ConvenioGroup,
    sedeFullKey: string,
  ) {
    const expanded = expandedSedes.has(sedeFullKey);
    return (
      <React.Fragment key={`sede-${sedeFullKey}`}>
        <TableRow
          className="bg-muted/10 hover:bg-muted/20 cursor-pointer"
          onClick={() => toggleSede(sedeFullKey)}
        >
          <TableCell className="py-1.5 text-sm font-medium">
            <RowLabel
              label={sede.ipressNombre}
              indent={3}
              expanded={expanded}
              onToggle={() => toggleSede(sedeFullKey)}
              badge={String(sede.universidades.length)}
            />
          </TableCell>
          {columns.map((col) => {
            const tot = sede.universidades.reduce(
              (s, u) => s + (u.celdas.get(col.key)?.autorizados ?? 0),
              0,
            );
            return (
              <TableCell
                key={col.key}
                className="px-2 text-center text-xs text-muted-foreground"
              >
                <CeldaNum n={tot} />
              </TableCell>
            );
          })}
          <TableCell className="border-l px-2 text-center text-xs font-semibold">
            <CeldaNum n={sede.totAutorizados} />
          </TableCell>
          {canWrite ? <TableCell /> : null}
        </TableRow>
        {expanded
          ? sede.universidades.map((u) => renderUnivRow(u, sede, convenio))
          : null}
      </React.Fragment>
    );
  }

  // ── renderizado de fila convenio
  function renderConvenioRow(
    convenio: ConvenioGroup,
    convenioFullKey: string,
  ) {
    const expanded = expandedConvenios.has(convenioFullKey);
    return (
      <React.Fragment key={`conv-${convenioFullKey}`}>
        <TableRow
          className="bg-muted/15 hover:bg-muted/25 cursor-pointer"
          onClick={() => toggleConvenio(convenioFullKey)}
        >
          <TableCell className="py-1.5 text-sm font-medium">
            <RowLabel
              label={convenio.convenioLabel}
              indent={2}
              expanded={expanded}
              onToggle={() => toggleConvenio(convenioFullKey)}
              badge={String(convenio.sedes.length)}
            />
          </TableCell>
          {columns.map((col) => {
            const tot = convenio.sedes.reduce(
              (s, sg) =>
                s +
                sg.universidades.reduce(
                  (ss, u) =>
                    ss + (u.celdas.get(col.key)?.autorizados ?? 0),
                  0,
                ),
              0,
            );
            return (
              <TableCell
                key={col.key}
                className="px-2 text-center text-xs text-muted-foreground"
              >
                <CeldaNum n={tot} />
              </TableCell>
            );
          })}
          <TableCell className="border-l px-2 text-center text-xs font-semibold">
            <CeldaNum n={convenio.totAutorizados} />
          </TableCell>
          {canWrite ? <TableCell /> : null}
        </TableRow>
        {expanded
          ? convenio.sedes.map((s) =>
              renderSedeRow(
                s,
                convenio,
                `${convenioFullKey}:${s.ipressKey}`,
              ),
            )
          : null}
      </React.Fragment>
    );
  }

  // ── renderizado de fila UE
  function renderUERow(ue: UEGroup, ambitoKey: string) {
    const ueFullKey = `${ambitoKey}:${ue.ueKey}`;
    const expanded = expandedUEs.has(ueFullKey);
    return (
      <React.Fragment key={`ue-${ueFullKey}`}>
        <TableRow
          className="bg-muted/25 hover:bg-muted/35 cursor-pointer"
          onClick={() => toggleUE(ueFullKey)}
        >
          <TableCell className="py-1.5 text-sm font-semibold">
            <RowLabel
              label={ue.ueNombre}
              indent={1}
              expanded={expanded}
              onToggle={() => toggleUE(ueFullKey)}
              badge={String(ue.convenios.length)}
            />
          </TableCell>
          {columns.map((col) => {
            const tot = ue.convenios.reduce(
              (s, c) =>
                s +
                c.sedes.reduce(
                  (ss, sg) =>
                    ss +
                    sg.universidades.reduce(
                      (sss, u) =>
                        sss + (u.celdas.get(col.key)?.autorizados ?? 0),
                      0,
                    ),
                  0,
                ),
              0,
            );
            return (
              <TableCell
                key={col.key}
                className="px-2 text-center text-xs text-muted-foreground"
              >
                <CeldaNum n={tot} />
              </TableCell>
            );
          })}
          <TableCell className="border-l px-2 text-center text-xs font-semibold">
            <CeldaNum n={ue.totAutorizados} />
          </TableCell>
          {canWrite ? <TableCell /> : null}
        </TableRow>
        {expanded
          ? ue.convenios.map((c) =>
              renderConvenioRow(c, `${ueFullKey}:${c.convenioKey}`),
            )
          : null}
      </React.Fragment>
    );
  }

  // ── renderizado de fila Ámbito
  function renderAmbitoRow(ambito: AmbitoGroup) {
    const expanded = expandedAmbitos.has(ambito.ambitoKey);
    return (
      <React.Fragment key={`ambito-${ambito.ambitoKey}`}>
        <TableRow
          className="bg-primary/5 hover:bg-primary/10 cursor-pointer"
          onClick={() => toggleAmbito(ambito.ambitoKey)}
        >
          <TableCell className="py-2 text-sm font-bold">
            <RowLabel
              label={ambito.ambitoNombre}
              indent={0}
              expanded={expanded}
              onToggle={() => toggleAmbito(ambito.ambitoKey)}
              badge={String(ambito.ues.length)}
            />
          </TableCell>
          {columns.map((col) => {
            return (
              <TableCell
                key={col.key}
                className="px-2 text-center text-xs font-semibold"
              >
                <CeldaNum
                  n={ambito.ues.reduce(
                    (s, u) =>
                      s +
                      u.convenios.reduce(
                        (ss, c) =>
                          ss +
                          c.sedes.reduce(
                            (sss, sg) =>
                              sss +
                              sg.universidades.reduce(
                                (ssss, univ) =>
                                  ssss +
                                  (univ.celdas.get(col.key)?.autorizados ?? 0),
                                0,
                              ),
                            0,
                          ),
                        0,
                      ),
                    0,
                  )}
                />
              </TableCell>
            );
          })}
          <TableCell className="border-l px-2 text-center text-xs font-bold">
            <CeldaNum n={ambito.totAutorizados} />
          </TableCell>
          {canWrite ? <TableCell /> : null}
        </TableRow>
        {expanded
          ? ambito.ues.map((u) => renderUERow(u, ambito.ambitoKey))
          : null}
      </React.Fragment>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* ── Barra de filtros ─────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Filtros izquierda */}
        <div className="w-36 shrink-0">
          <EntityCombobox
            endpoint="academic-levels"
            value={nivel}
            onChange={(id) => {
              setNivelPicked(id as number | null);
              setFilterCarreraId(null);
            }}
            placeholder="Nivel…"
          />
        </div>

        <div className="w-44 shrink-0">
          <EntityCombobox
            endpoint="health-geographic-scopes"
            value={filterAmbitoId}
            onChange={(id) => setFilterAmbitoId(id as number | null)}
            placeholder="Ámbito…"
          />
        </div>

        <div className="w-52 shrink-0">
          <EntityCombobox
            endpoint="executing-units"
            valueKey="codigo"
            value={filterUeId}
            onChange={(v) => setFilterUeId(v as string | null)}
            placeholder="Unidad Ejecutora…"
          />
        </div>

        <div className="w-52 shrink-0">
          <EntityCombobox
            endpoint="ipress"
            valueKey="codigo_renipress"
            params={{ es_sede_docente: "true" }}
            toLabel={ipressLabel}
            value={filterIpress}
            onChange={(v) => setFilterIpress(v as string | null)}
            placeholder="Sede docente…"
          />
        </div>

        <div className="w-44 shrink-0">
          <EntityCombobox
            endpoint="universities"
            value={filterUnivId}
            onChange={(id) => setFilterUnivId(id as number | null)}
            placeholder="Universidad…"
          />
        </div>

        <div className="w-44 shrink-0">
          {esPregrado ? (
            <EntityCombobox
              key="carrera-filter"
              endpoint="professional-careers"
              params={nivel ? { nivel_academico: String(nivel) } : {}}
              value={filterCarreraId}
              onChange={(id) => setFilterCarreraId(id as number | null)}
              placeholder="Carrera…"
            />
          ) : (
            <EntityCombobox
              key="esp-filter"
              endpoint="specialties"
              value={filterCarreraId}
              onChange={(id) => setFilterCarreraId(id as number | null)}
              placeholder="Especialidad…"
            />
          )}
        </div>

        {hasFilters ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearFilters}
            className="h-9 px-2 text-muted-foreground hover:text-foreground"
          >
            <X className="size-3.5 mr-1" />
            Limpiar
          </Button>
        ) : null}

        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar…"
          className="h-9 w-44"
        />

        {/* Acciones derecha */}
        <div className="ml-auto flex items-center gap-2">
          <ClinicalAllocationsBulkUploadDialog />
          {canWrite ? (
            <Button onClick={() => setNuevoOpen(true)}>Nuevo</Button>
          ) : null}
        </div>
      </div>

      {/* ── Tabla matriz ─────────────────────────────────────────────── */}
      <div className="rounded-md border overflow-auto">
        <Table className="w-full text-xs">
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead className="text-xs h-10 min-w-[260px] sticky left-0 bg-muted/50">
                Ámbito / UE / Convenio / Sede / Universidad
              </TableHead>
              {columns.map((col) => (
                <TableHead
                  key={col.key}
                  className="text-xs h-10 text-center px-2 min-w-[90px]"
                  title={col.label}
                >
                  <span className="block max-w-[80px] truncate mx-auto">
                    {col.label}
                  </span>
                </TableHead>
              ))}
              <TableHead className="text-xs h-10 text-center px-2 border-l min-w-[80px] font-semibold">
                Total autor.
              </TableHead>
              {canWrite ? (
                <TableHead className="text-xs h-10 w-20" />
              ) : null}
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.isLoading ? (
              <TableRow>
                <TableCell
                  colSpan={totalCols}
                  className="h-32 text-center text-muted-foreground"
                >
                  Cargando…
                </TableCell>
              </TableRow>
            ) : matrix.ambitos.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={totalCols}
                  className="h-32 text-center text-muted-foreground"
                >
                  {hasFilters
                    ? "Sin resultados para los filtros aplicados."
                    : "Sin asignaciones registradas."}
                </TableCell>
              </TableRow>
            ) : (
              matrix.ambitos.map((a) => renderAmbitoRow(a))
            )}
          </TableBody>
        </Table>
      </div>

      {/* ── Diálogos ─────────────────────────────────────────────────── */}
      <NuevaAsignacionDialog
        open={nuevoOpen}
        onOpenChange={setNuevoOpen}
        onSuccess={() => setAutoExpanded(false)}
        pregradoId={pregradoId}
      />

      {editingLeaf ? (
        <EditarAsignacionDialog
          open={editOpen}
          onOpenChange={(v) => {
            setEditOpen(v);
            if (!v) setEditingLeaf(null);
          }}
          ipressNombre={editingLeaf.ipressNombre}
          univNombre={editingLeaf.univNombre}
          convenioLabel={editingLeaf.convenioLabel}
          rows={editingLeaf.rows}
          esPregrado={esPregrado}
          onSuccess={() => {
            qc.invalidateQueries({
              queryKey: resourceKeys.all("clinical-field-allocations"),
            });
          }}
        />
      ) : null}

      {/* Confirmación borrado en lote */}
      <Dialog
        open={deletingLeaf !== null}
        onOpenChange={(v) => {
          if (!v) setDeletingLeaf(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar asignaciones</DialogTitle>
            <DialogDescription>
              Se eliminarán{" "}
              <strong>
                {deletingLeaf?.ids.length ?? 0} asignación
                {(deletingLeaf?.ids.length ?? 0) !== 1 ? "es" : ""}
              </strong>{" "}
              de <em>{deletingLeaf?.label}</em>. Esta acción no se puede
              deshacer.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeletingLeaf(null)}
              disabled={bulkDeleteM.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (deletingLeaf) bulkDeleteM.mutate(deletingLeaf.ids);
              }}
              disabled={bulkDeleteM.isPending}
            >
              {bulkDeleteM.isPending ? "Eliminando…" : "Eliminar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
