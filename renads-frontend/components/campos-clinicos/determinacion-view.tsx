"use client";

import React, { useMemo, useState } from "react";
import { Pencil, Trash2, X } from "lucide-react";
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
import { Label } from "@/components/ui/label";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ClinicalRegistrationsBulkUploadDialog } from "@/components/campos-clinicos/clinical-registrations-bulk-upload-dialog";
import { NuevaDeterminacionDialog } from "@/components/campos-clinicos/nueva-determinacion-dialog";
import { EditarSedeDialog } from "@/components/campos-clinicos/editar-sede-dialog";

// ─── tipos ───────────────────────────────────────────────────────────────────

type Metrica = "registrados" | "asignados" | "disponibles" | "todos";

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
  registrados: number;
  asignados: number;
  disponibles: number;
  rowIds: number[];
}

interface SedeRow {
  ipressKey: string;
  ipressNombre: string;
  celdas: Map<string, CeldaData>;
  totReg: number;
  totAsig: number;
  totDisp: number;
}

interface UEGroup {
  ueKey: string;
  ueNombre: string;
  sedes: SedeRow[];
  totReg: number;
  totAsig: number;
  totDisp: number;
}

interface AmbitoGroup {
  ambitoKey: string;
  ambitoNombre: string;
  ues: UEGroup[];
  totReg: number;
  totAsig: number;
  totDisp: number;
}

interface MatrixData {
  columns: ColDef[];
  ambitos: AmbitoGroup[];
}

// ─── helpers ─────────────────────────────────────────────────────────────────

function nestedNombre(v: unknown): string {
  if (!v || typeof v !== "object") return "";
  return String((v as Record<string, unknown>).nombre ?? "");
}

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
  const colMap = new Map<string, string>(); // key -> label
  const ambitoMap = new Map<string, { nombre: string; ues: Map<string, { nombre: string; sedesMap: Map<string, SedeRow> }> }>();

  for (const row of rows) {
    const ip = (row.ipress_detalle ?? {}) as IpressDetalle;
    const ags = ip.ambito_geografico_sanitario;
    const ue = ip.unidad_ejecutora;

    const ambitoKey = ags ? `${ags.id}` : "sin-ambito";
    const ambitoNombre = ags?.nombre ?? "Sin ámbito";
    const ueKey = ue ? `${ue.id}` : "sin-ue";
    const ueNombre = ue?.nombre ?? "Sin unidad ejecutora";
    const ipressKey = `${ip.id ?? row.ipress}`;

    const colKey = getColKey(row, esPregrado);
    const colLabel = getColLabel(row, esPregrado);
    colMap.set(colKey, colLabel);

    if (!ambitoMap.has(ambitoKey)) {
      ambitoMap.set(ambitoKey, { nombre: ambitoNombre, ues: new Map() });
    }
    const ambitoEntry = ambitoMap.get(ambitoKey)!;

    if (!ambitoEntry.ues.has(ueKey)) {
      ambitoEntry.ues.set(ueKey, { nombre: ueNombre, sedesMap: new Map() });
    }
    const ueEntry = ambitoEntry.ues.get(ueKey)!;

    if (!ueEntry.sedesMap.has(ipressKey)) {
      ueEntry.sedesMap.set(ipressKey, {
        ipressKey,
        ipressNombre: ip.nombre ?? "—",
        celdas: new Map(),
        totReg: 0,
        totAsig: 0,
        totDisp: 0,
      });
    }
    const sede = ueEntry.sedesMap.get(ipressKey)!;
    const reg = Number(row.campos_clinicos_registrados) || 0;
    const asig = Number(row.campos_clinicos_asignados) || 0;
    const disp = Number(row.disponibilidad) || 0;
    const existing = sede.celdas.get(colKey);
    if (existing) {
      sede.celdas.set(colKey, {
        registrados: existing.registrados + reg,
        asignados: existing.asignados + asig,
        disponibles: existing.disponibles + disp,
        rowIds: [...existing.rowIds, row.id],
      });
    } else {
      sede.celdas.set(colKey, { registrados: reg, asignados: asig, disponibles: disp, rowIds: [row.id] });
    }
    sede.totReg += reg;
    sede.totAsig += asig;
    sede.totDisp += disp;
  }

  const columns: ColDef[] = Array.from(colMap.entries())
    .map(([key, label]) => ({ key, label }))
    .sort((a, b) => a.label.localeCompare(b.label, "es"));

  const ambitos: AmbitoGroup[] = Array.from(ambitoMap.entries()).map(([ambitoKey, ambitoEntry]) => {
    const ues: UEGroup[] = Array.from(ambitoEntry.ues.entries()).map(([ueKey, ueEntry]) => {
      const sedes: SedeRow[] = Array.from(ueEntry.sedesMap.values()).sort((a, b) =>
        a.ipressNombre.localeCompare(b.ipressNombre, "es"),
      );
      return {
        ueKey,
        ueNombre: ueEntry.nombre,
        sedes,
        totReg: sedes.reduce((s, r) => s + r.totReg, 0),
        totAsig: sedes.reduce((s, r) => s + r.totAsig, 0),
        totDisp: sedes.reduce((s, r) => s + r.totDisp, 0),
      };
    }).sort((a, b) => a.ueNombre.localeCompare(b.ueNombre, "es"));

    return {
      ambitoKey,
      ambitoNombre: ambitoEntry.nombre,
      ues,
      totReg: ues.reduce((s, u) => s + u.totReg, 0),
      totAsig: ues.reduce((s, u) => s + u.totAsig, 0),
      totDisp: ues.reduce((s, u) => s + u.totDisp, 0),
    };
  }).sort((a, b) => a.ambitoNombre.localeCompare(b.ambitoNombre, "es"));

  return { columns, ambitos };
}

// ─── celdas de valor ─────────────────────────────────────────────────────────

function CeldaNum({ n, warn }: { n: number; warn?: boolean }) {
  if (n === 0) return <span className="text-muted-foreground/50">—</span>;
  return <span className={`tabular-nums font-medium ${warn ? "text-destructive" : ""}`}>{n}</span>;
}

function CeldaTodos({ data }: { data: CeldaData | undefined }) {
  const r = data?.registrados ?? 0;
  const a = data?.asignados ?? 0;
  const d = data?.disponibles ?? 0;
  return (
    <>
      <TableCell className="px-1.5 text-center text-xs"><CeldaNum n={r} /></TableCell>
      <TableCell className="px-1.5 text-center text-xs"><CeldaNum n={a} /></TableCell>
      <TableCell className="px-1.5 text-center text-xs"><CeldaNum n={d} warn={d === 0 && r > 0} /></TableCell>
    </>
  );
}

function CeldaSingle({ data, metrica }: { data: CeldaData | undefined; metrica: Exclude<Metrica, "todos"> }) {
  const n = data
    ? metrica === "registrados" ? data.registrados
      : metrica === "asignados" ? data.asignados
      : data.disponibles
    : 0;
  return (
    <TableCell className="px-2 text-center text-xs">
      <CeldaNum n={n} warn={metrica === "disponibles" && n === 0 && (data?.registrados ?? 0) > 0} />
    </TableCell>
  );
}

// ─── etiqueta de fila ─────────────────────────────────────────────────────────

function RowLabel({ label, indent, badge }: { label: string; indent: 0 | 1 | 2; badge?: string }) {
  const pl = indent === 0 ? "" : indent === 1 ? "pl-4" : "pl-8";
  return (
    <span className={`flex items-center gap-1.5 ${pl}`}>
      <span className="truncate max-w-xs">{label}</span>
      {badge ? (
        <span className="shrink-0 rounded bg-muted px-1 py-0.5 text-[10px] text-muted-foreground">
          {badge}
        </span>
      ) : null}
    </span>
  );
}

// ─── componente principal ─────────────────────────────────────────────────────

const ipressLabel = (r: WithId) =>
  [r.codigo_renipress, r.nombre].filter(Boolean).join(" — ") || String(r.id);

export function DeterminacionView() {
  const user = useAuthStore((s) => s.user);
  const canWrite = userHasRole(user, "CONAPRES", "Administrador RENADS");

  // ── nivel académico (para columnas: Pregrado=carreras, otros=especialidades)
  const nivelesQuery = useQuery({
    queryKey: ["academic-levels", "for-campos-clinicos"],
    queryFn: () =>
      api.get<Paginated<WithId>>("/academic-levels/").then((r) => r.data.results),
    staleTime: 10 * 60_000,
  });
  const niveles = useMemo(() => nivelesQuery.data ?? [], [nivelesQuery.data]);
  const pregradoId = useMemo<number | null>(() => {
    const p = niveles.find((l) => String(l.nombre ?? "").toLowerCase().includes("pregrado"));
    return p ? Number(p.id) : null;
  }, [niveles]);
  const [nivelPicked, setNivelPicked] = useState<number | null>(null);
  const nivel = nivelPicked ?? pregradoId;
  const esPregrado = nivel === pregradoId && pregradoId !== null;

  // ── filtros server-side
  const [filterIpress, setFilterIpress] = useState<string | null>(null);
  const [filterCarrera, setFilterCarrera] = useState<number | null>(null);

  // ── filtros client-side
  const [filterAmbitoId, setFilterAmbitoId] = useState<number | null>(null);
  const [filterUeId, setFilterUeId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);

  // ── métrica
  const [metrica, setMetrica] = useState<Metrica>("registrados");

  // ── expand state
  const [expandedAmbitos, setExpandedAmbitos] = useState<Set<string>>(new Set());
  const [expandedUEs, setExpandedUEs] = useState<Set<string>>(new Set());

  // ── CRUD state
  const qc = useQueryClient();
  const [nuevoOpen, setNuevoOpen] = useState(false);
  const [editSedeOpen, setEditSedeOpen] = useState(false);
  const [editingSede, setEditingSede] = useState<{ ipressNombre: string; rows: WithId[] } | null>(null);
  const [deletingSede, setDeletingSede] = useState<{ ipressNombre: string; rows: WithId[] } | null>(null);

  // ── data
  const hooks = useMemo(
    () => createResourceHooks<WithId, Record<string, unknown>>("clinical-field-registrations"),
    [],
  );

  const list = hooks.useList({
    ordering: "ipress__nombre,carrera_profesional__nombre",
    filters: {
      ...(filterIpress ? { ipress: filterIpress } : {}),
      ...(filterCarrera ? { carrera_profesional: filterCarrera } : {}),
      ...(nivel ? { "carrera_profesional__nivel_academico": String(nivel) } : {}),
      page_size: 500,
    },
  });

  const bulkDeleteM = useMutation({
    mutationFn: async (ids: number[]) => {
      const results = await Promise.allSettled(
        ids.map((id) => api.delete(`/clinical-field-registrations/${id}/`)),
      );
      const errors = results.filter(
        (r): r is PromiseRejectedResult => r.status === "rejected",
      );
      return { deleted: ids.length - errors.length, errors };
    },
    onSuccess: ({ deleted, errors }) => {
      qc.invalidateQueries({ queryKey: resourceKeys.all("clinical-field-registrations") });
      if (deleted > 0) {
        toast.success(`${deleted} registro${deleted !== 1 ? "s" : ""} eliminado${deleted !== 1 ? "s" : ""}.`);
        setAutoExpanded(false);
      }
      if (errors.length > 0) toast.error(`${errors.length} no se pudo${errors.length !== 1 ? "n" : ""} eliminar.`);
      setDeletingSede(null);
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
        const ue = ip?.unidad_ejecutora;
        return ue ? String(ue.id) === filterUeId : false;
      });
    }
    if (debouncedSearch.trim()) {
      const q = debouncedSearch.toLowerCase();
      rows = rows.filter((r) => {
        const ip = r.ipress_detalle as IpressDetalle | null;
        const cp = r.carrera_profesional_detalle as WithId | null;
        const esp = r.especialidad_detalle as WithId | null;
        return [
          ip?.ambito_geografico_sanitario?.nombre ?? "",
          ip?.unidad_ejecutora?.nombre ?? "",
          ip?.nombre ?? "",
          String(cp?.nombre ?? ""),
          String(esp?.nombre ?? ""),
        ].join(" ").toLowerCase().includes(q);
      });
    }
    return rows;
  }, [list.data, filterAmbitoId, filterUeId, debouncedSearch]);

  const matrix = useMemo(() => buildMatrix(filteredRows, esPregrado), [filteredRows, esPregrado]);

  // ── expand toggles (default: todos expandidos al cargar)
  const allAmbitoKeys = useMemo(() => matrix.ambitos.map((a) => a.ambitoKey), [matrix]);
  const allUEKeys = useMemo(
    () => matrix.ambitos.flatMap((a) => a.ues.map((u) => `${a.ambitoKey}:${u.ueKey}`)),
    [matrix],
  );

  // Auto-expand todo cuando llegan datos por primera vez
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
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }
  function toggleUE(key: string) {
    setExpandedUEs((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }


  const hasFilters = !!(filterAmbitoId || filterUeId || filterIpress || filterCarrera || search);
  function clearFilters() {
    setFilterAmbitoId(null);
    setFilterUeId(null);
    setFilterIpress(null);
    setFilterCarrera(null);
    setSearch("");
  }

  // ── columnas de tabla
  const { columns } = matrix;
  const isTodos = metrica === "todos";
  // número de celdas de datos por fila (para colSpan de mensajes)
  const dataCols = isTodos ? columns.length * 3 + 3 : columns.length + 1;
  const totalCols = 1 + dataCols + (canWrite ? 1 : 0);

  // ─── renderizado de fila sede ─────────────────────────────────────────────
  function renderSedeRow(sede: SedeRow) {
    return (
      <TableRow key={sede.ipressKey} className="hover:bg-muted/30">
        <TableCell className="py-1.5 text-sm">
          <RowLabel label={sede.ipressNombre} indent={2} />
        </TableCell>

        {isTodos ? (
          <>
            {columns.map((col) => (
              <CeldaTodos key={col.key} data={sede.celdas.get(col.key)} />
            ))}
            {/* total row */}
            <TableCell className="border-l px-1.5 text-center text-xs font-semibold">
              <CeldaNum n={sede.totReg} />
            </TableCell>
            <TableCell className="px-1.5 text-center text-xs font-semibold">
              <CeldaNum n={sede.totAsig} />
            </TableCell>
            <TableCell className="px-1.5 text-center text-xs font-semibold">
              <CeldaNum n={sede.totDisp} warn={sede.totDisp === 0 && sede.totReg > 0} />
            </TableCell>
          </>
        ) : (
          <>
            {columns.map((col) => (
              <CeldaSingle
                key={col.key}
                data={sede.celdas.get(col.key)}
                metrica={metrica as Exclude<Metrica, "todos">}
              />
            ))}
            {/* total row */}
            <TableCell className="border-l px-2 text-center text-xs font-semibold">
              <CeldaNum
                n={
                  metrica === "registrados" ? sede.totReg
                    : metrica === "asignados" ? sede.totAsig
                    : sede.totDisp
                }
                warn={metrica === "disponibles" && sede.totDisp === 0 && sede.totReg > 0}
              />
            </TableCell>
          </>
        )}

        {canWrite ? (
          <TableCell className="py-1 pr-2">
            <div className="flex justify-end gap-1">
              <Button
                variant="outline"
                size="icon-sm"
                aria-label="Editar determinaciones de esta sede"
                title="Editar determinaciones"
                onClick={() => {
                  const sedeRows = Array.from(sede.celdas.values())
                    .flatMap((c) => c.rowIds.map((id) => list.data?.results?.find((r) => r.id === id)))
                    .filter((r): r is WithId => r !== undefined);
                  setEditingSede({ ipressNombre: sede.ipressNombre, rows: sedeRows });
                  setEditSedeOpen(true);
                }}
              >
                <Pencil />
              </Button>
              <Button
                variant="destructive"
                size="icon-sm"
                aria-label="Eliminar todas las determinaciones de esta sede"
                title="Eliminar todas"
                onClick={() => {
                  const sedeRows = Array.from(sede.celdas.values())
                    .flatMap((c) => c.rowIds.map((id) => list.data?.results?.find((r) => r.id === id)))
                    .filter((r): r is WithId => r !== undefined);
                  setDeletingSede({ ipressNombre: sede.ipressNombre, rows: sedeRows });
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

  // ─── renderizado de fila UE (subtotal) ────────────────────────────────────
  function renderUERow(ue: UEGroup, ambitoKey: string) {
    const ueFullKey = `${ambitoKey}:${ue.ueKey}`;
    const isOpen = expandedUEs.has(ueFullKey);
    return (
      <React.Fragment key={ue.ueKey}>
        <TableRow
          className="cursor-pointer bg-muted/25 hover:bg-muted/40 font-medium"
          onClick={() => toggleUE(ueFullKey)}
        >
          <TableCell className="py-2 text-sm">
            <RowLabel
              label={ue.ueNombre}
              indent={1}
              badge={`${ue.sedes.length} sede${ue.sedes.length === 1 ? "" : "s"}`}
            />
          </TableCell>

          {isTodos ? (
            <>
              {columns.map((col) => {
                const r = ue.sedes.reduce((s, sede) => s + (sede.celdas.get(col.key)?.registrados ?? 0), 0);
                const a = ue.sedes.reduce((s, sede) => s + (sede.celdas.get(col.key)?.asignados ?? 0), 0);
                const d = ue.sedes.reduce((s, sede) => s + (sede.celdas.get(col.key)?.disponibles ?? 0), 0);
                return (
                  <React.Fragment key={col.key}>
                    <TableCell className="px-1.5 text-center text-xs"><CeldaNum n={r} /></TableCell>
                    <TableCell className="px-1.5 text-center text-xs"><CeldaNum n={a} /></TableCell>
                    <TableCell className="px-1.5 text-center text-xs"><CeldaNum n={d} warn={d === 0 && r > 0} /></TableCell>
                  </React.Fragment>
                );
              })}
              <TableCell className="border-l px-1.5 text-center text-xs font-bold"><CeldaNum n={ue.totReg} /></TableCell>
              <TableCell className="px-1.5 text-center text-xs font-bold"><CeldaNum n={ue.totAsig} /></TableCell>
              <TableCell className="px-1.5 text-center text-xs font-bold"><CeldaNum n={ue.totDisp} warn={ue.totDisp === 0 && ue.totReg > 0} /></TableCell>
            </>
          ) : (
            <>
              {columns.map((col) => {
                const n = ue.sedes.reduce((s, sede) => {
                  const c = sede.celdas.get(col.key);
                  return s + (metrica === "registrados" ? (c?.registrados ?? 0) : metrica === "asignados" ? (c?.asignados ?? 0) : (c?.disponibles ?? 0));
                }, 0);
                return <TableCell key={col.key} className="px-2 text-center text-xs"><CeldaNum n={n} /></TableCell>;
              })}
              <TableCell className="border-l px-2 text-center text-xs font-bold">
                <CeldaNum
                  n={metrica === "registrados" ? ue.totReg : metrica === "asignados" ? ue.totAsig : ue.totDisp}
                  warn={metrica === "disponibles" && ue.totDisp === 0 && ue.totReg > 0}
                />
              </TableCell>
            </>
          )}

          {canWrite ? <TableCell /> : null}
        </TableRow>

        {isOpen ? ue.sedes.map((sede) => renderSedeRow(sede)) : null}
      </React.Fragment>
    );
  }

  // ─── renderizado de fila ámbito (total) ───────────────────────────────────
  function renderAmbitoRow(ambito: AmbitoGroup) {
    const isOpen = expandedAmbitos.has(ambito.ambitoKey);
    return (
      <React.Fragment key={ambito.ambitoKey}>
        <TableRow
          className="cursor-pointer bg-primary/5 hover:bg-primary/10 font-semibold"
          onClick={() => toggleAmbito(ambito.ambitoKey)}
        >
          <TableCell className="py-2.5 text-sm">
            <RowLabel
              label={ambito.ambitoNombre}
              indent={0}
              badge={`${ambito.ues.length} UE`}
            />
          </TableCell>

          {isTodos ? (
            <>
              {columns.map((col) => {
                const r = ambito.ues.reduce((s, ue) => s + ue.sedes.reduce((ss, sede) => ss + (sede.celdas.get(col.key)?.registrados ?? 0), 0), 0);
                const a = ambito.ues.reduce((s, ue) => s + ue.sedes.reduce((ss, sede) => ss + (sede.celdas.get(col.key)?.asignados ?? 0), 0), 0);
                const d = ambito.ues.reduce((s, ue) => s + ue.sedes.reduce((ss, sede) => ss + (sede.celdas.get(col.key)?.disponibles ?? 0), 0), 0);
                return (
                  <React.Fragment key={col.key}>
                    <TableCell className="px-1.5 text-center text-xs"><CeldaNum n={r} /></TableCell>
                    <TableCell className="px-1.5 text-center text-xs"><CeldaNum n={a} /></TableCell>
                    <TableCell className="px-1.5 text-center text-xs"><CeldaNum n={d} warn={d === 0 && r > 0} /></TableCell>
                  </React.Fragment>
                );
              })}
              <TableCell className="border-l px-1.5 text-center text-xs font-bold"><CeldaNum n={ambito.totReg} /></TableCell>
              <TableCell className="px-1.5 text-center text-xs font-bold"><CeldaNum n={ambito.totAsig} /></TableCell>
              <TableCell className="px-1.5 text-center text-xs font-bold"><CeldaNum n={ambito.totDisp} warn={ambito.totDisp === 0 && ambito.totReg > 0} /></TableCell>
            </>
          ) : (
            <>
              {columns.map((col) => {
                const n = ambito.ues.reduce((s, ue) => s + ue.sedes.reduce((ss, sede) => {
                  const c = sede.celdas.get(col.key);
                  return ss + (metrica === "registrados" ? (c?.registrados ?? 0) : metrica === "asignados" ? (c?.asignados ?? 0) : (c?.disponibles ?? 0));
                }, 0), 0);
                return <TableCell key={col.key} className="px-2 text-center text-xs"><CeldaNum n={n} /></TableCell>;
              })}
              <TableCell className="border-l px-2 text-center text-xs font-bold">
                <CeldaNum
                  n={metrica === "registrados" ? ambito.totReg : metrica === "asignados" ? ambito.totAsig : ambito.totDisp}
                  warn={metrica === "disponibles" && ambito.totDisp === 0 && ambito.totReg > 0}
                />
              </TableCell>
            </>
          )}

          {canWrite ? <TableCell /> : null}
        </TableRow>

        {isOpen ? ambito.ues.map((ue) => renderUERow(ue, ambito.ambitoKey)) : null}
      </React.Fragment>
    );
  }

  // ─── encabezado de tabla ──────────────────────────────────────────────────
  function renderTableHeader() {
    const colLabel = esPregrado ? "Carrera profesional" : "Especialidad";
    if (isTodos) {
      return (
        <TableHeader>
          {/* fila 1: jerarquía | nombre de carrera (colspan 3) | Total (colspan 3) */}
          <TableRow className="border-b-0">
            <TableHead rowSpan={2} className="align-middle border-r min-w-[220px]">
              Ámbito / Unidad Ejecutora / Sede docente
            </TableHead>
            {columns.map((col) => (
              <TableHead
                key={col.key}
                colSpan={3}
                className="border-l text-center text-xs font-semibold"
              >
                <span className="block truncate max-w-[12rem] mx-auto" title={col.label}>
                  {col.label}
                </span>
              </TableHead>
            ))}
            <TableHead colSpan={3} className="border-l text-center text-xs font-bold">
              Total {colLabel}
            </TableHead>
            {canWrite ? <TableHead rowSpan={2} /> : null}
          </TableRow>
          {/* fila 2: D / A / V por cada carrera + D/A/V del total */}
          <TableRow>
            {columns.map((col) => (
              <React.Fragment key={col.key}>
                <TableHead className="border-l px-1.5 text-center text-[10px] text-muted-foreground w-10">Det</TableHead>
                <TableHead className="px-1.5 text-center text-[10px] text-muted-foreground w-10">Asig</TableHead>
                <TableHead className="px-1.5 text-center text-[10px] text-muted-foreground w-10">Disp</TableHead>
              </React.Fragment>
            ))}
            <TableHead className="border-l px-1.5 text-center text-[10px] text-muted-foreground w-10">Det</TableHead>
            <TableHead className="px-1.5 text-center text-[10px] text-muted-foreground w-10">Asig</TableHead>
            <TableHead className="px-1.5 text-center text-[10px] text-muted-foreground w-10">Disp</TableHead>
          </TableRow>
        </TableHeader>
      );
    }

    const metricaLabel =
      metrica === "registrados" ? "Determinados"
      : metrica === "asignados" ? "Asignados"
      : "Disponibles";

    return (
      <TableHeader>
        <TableRow>
          <TableHead className="min-w-[220px]">Ámbito / Unidad Ejecutora / Sede docente</TableHead>
          {columns.map((col) => (
            <TableHead key={col.key} className="px-2 text-center text-xs">
              <span className="block truncate max-w-[10rem] mx-auto" title={col.label}>
                {col.label}
              </span>
            </TableHead>
          ))}
          <TableHead className="border-l px-2 text-center text-xs font-bold">
            Total {metricaLabel}
          </TableHead>
          {canWrite ? <TableHead className="w-24" /> : null}
        </TableRow>
      </TableHeader>
    );
  }

  // ─── render ───────────────────────────────────────────────────────────────
  return (
    <div>
      {/* ── Barra única: filtros + acciones ── */}
      <div className="mb-3 flex flex-wrap items-end gap-2">
        {/* Nivel académico — primero, determina si columnas = carreras o especialidades */}
        <div className="grid gap-1">
          <Label className="text-xs text-muted-foreground">Nivel académico</Label>
          <div className="w-40">
            <EntityCombobox
              endpoint="academic-levels"
              value={nivel}
              onChange={(id) => {
                setNivelPicked(id as number | null);
                setAutoExpanded(false);
              }}
              placeholder="Todos"
            />
          </div>
        </div>

        {/* Ámbito */}
        <div className="grid gap-1">
          <Label className="text-xs text-muted-foreground">Ámbito geográfico</Label>
          <div className="w-44">
            <EntityCombobox
              endpoint="health-geographic-scopes"
              value={filterAmbitoId}
              onChange={setFilterAmbitoId}
              placeholder="Todos"
            />
          </div>
        </div>

        {/* Unidad ejecutora */}
        <div className="grid gap-1">
          <Label className="text-xs text-muted-foreground">Unidad ejecutora</Label>
          <div className="w-48">
            <EntityCombobox
              endpoint="executing-units"
              valueKey="codigo"
              value={filterUeId}
              onChange={setFilterUeId}
              placeholder="Todas"
            />
          </div>
        </div>

        {/* Sede docente */}
        <div className="grid gap-1">
          <Label className="text-xs text-muted-foreground">Sede docente</Label>
          <div className="w-56">
            <EntityCombobox
              endpoint="ipress"
              valueKey="codigo_renipress"
              params={{ es_sede_docente: "true" }}
              toLabel={ipressLabel}
              value={filterIpress}
              onChange={setFilterIpress}
              placeholder="Todas"
            />
          </div>
        </div>

        {/* Carrera profesional */}
        <div className="grid gap-1">
          <Label className="text-xs text-muted-foreground">Carrera profesional</Label>
          <div className="w-44">
            <EntityCombobox
              endpoint="professional-careers"
              value={filterCarrera}
              onChange={setFilterCarrera}
              placeholder="Todas"
            />
          </div>
        </div>

        {/* Limpiar filtros */}
        {hasFilters ? (
          <Button variant="ghost" size="sm" className="h-8 gap-1.5" onClick={clearFilters}>
            <X className="size-3.5" /> Limpiar
          </Button>
        ) : null}

        {/* Búsqueda texto */}
        <div className="grid gap-1">
          <Label className="text-xs text-muted-foreground">Buscar</Label>
          <Input
            placeholder="Ámbito, UE, sede, carrera…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 w-52"
          />
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Acciones */}
        {canWrite ? (
          <div className="flex items-end gap-2">
            <ClinicalRegistrationsBulkUploadDialog />
            <Button
              size="sm"
              onClick={() => setNuevoOpen(true)}
            >
              Nuevo
            </Button>
          </div>
        ) : null}
      </div>

      {/* ── Controles de visualización ── */}
      <div className="mb-3 flex flex-wrap items-center gap-3">
        {/* Métrica */}
        <div className="flex items-center gap-1.5">
          <Label className="whitespace-nowrap text-xs text-muted-foreground">Campos de formación:</Label>
          <Select
            value={metrica}
            onValueChange={(v) => setMetrica(v as Metrica)}
          >
            <SelectTrigger className="h-8 w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="registrados">Determinados</SelectItem>
              <SelectItem value="asignados">Asignados</SelectItem>
              <SelectItem value="disponibles">Disponibles</SelectItem>
              <SelectItem value="todos">Todos (Det / Asig / Disp)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <span className="text-xs text-muted-foreground">
          {filteredRows.length} {filteredRows.length === 1 ? "registro" : "registros"}
          {list.isFetching ? " · actualizando…" : ""}
        </span>
      </div>

      {/* ── Tabla Matriz ── */}
      {list.isError ? (
        <div className="rounded-md border border-destructive/30 p-4">
          <p className="text-sm text-destructive">No se pudo cargar el listado.</p>
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={() => list.refetch()}
            disabled={list.isFetching}
          >
            {list.isFetching ? "Reintentando…" : "Reintentar"}
          </Button>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border">
          <Table className="min-w-max">
            {renderTableHeader()}
            <TableBody>
              {list.isLoading ? (
                <TableRow>
                  <TableCell colSpan={totalCols} className="py-8 text-center text-sm text-muted-foreground">
                    Cargando…
                  </TableCell>
                </TableRow>
              ) : matrix.ambitos.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={totalCols} className="py-8 text-center text-sm text-muted-foreground">
                    Sin resultados.
                  </TableCell>
                </TableRow>
              ) : (
                matrix.ambitos.map((ambito) => renderAmbitoRow(ambito))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {/* ── Nuevo (batch) ── */}
      <NuevaDeterminacionDialog
        open={nuevoOpen}
        onOpenChange={setNuevoOpen}
        onSuccess={() => setAutoExpanded(false)}
        pregradoId={pregradoId}
      />

      {/* ── Editar sede (batch) ── */}
      <EditarSedeDialog
        open={editSedeOpen}
        onOpenChange={(v) => {
          setEditSedeOpen(v);
          if (!v) setEditingSede(null);
        }}
        ipressNombre={editingSede?.ipressNombre ?? ""}
        rows={editingSede?.rows ?? []}
        esPregrado={esPregrado}
        onSuccess={() => setAutoExpanded(false)}
      />

      {/* ── Eliminar sede (bulk) ── */}
      <Dialog
        open={deletingSede !== null}
        onOpenChange={(v) => { if (!v) setDeletingSede(null); }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar determinaciones — {deletingSede?.ipressNombre}</DialogTitle>
            <DialogDescription>
              Se eliminarán {deletingSede?.rows.length ?? 0} registro
              {(deletingSede?.rows.length ?? 0) !== 1 ? "s" : ""}. Esta acción no se puede deshacer.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeletingSede(null)}
              disabled={bulkDeleteM.isPending}
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (!deletingSede) return;
                bulkDeleteM.mutate(deletingSede.rows.map((r) => r.id));
              }}
              disabled={bulkDeleteM.isPending}
            >
              {bulkDeleteM.isPending ? "Procesando…" : "Eliminar todos"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
