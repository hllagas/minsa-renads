"use client";

import React, { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import { useForm, Controller, useWatch } from "react-hook-form";
import {
  useQuery,
  useMutation,
  useQueries,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Loader2,
  Search,
  Pencil,
  Trash2,
  Plus,
  Building2,
} from "lucide-react";

import { api, type Paginated } from "@/lib/api/client";
import type { WithId } from "@/lib/api/query";
import { extractApiError } from "@/lib/api/errors";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { EntityCombobox } from "@/components/form/entity-combobox";
import { DatePicker } from "@/components/form/date-picker";
import { AnnexChecklistAction } from "@/components/almacenamiento/annex-checklist-dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ---------- Types ----------

interface Representative extends WithId {
  nombre: string;
  numero_documento_identidad: string;
  sexo: "M" | "F";
  fecha_inicio_designacion: string;
  numero_resolucion_designacion: string | null;
  fecha_inicio_facultades: string | null;
  organo_directorio: number;
  cargo_ejecutivo: number;
  tipo_documento_identidad: number;
  activo: boolean;
}

interface OrgDirectory extends WithId {
  nombre: string;
  gobierno_regional: number | null;
  categoria: string;
}

interface ExecPosition extends WithId {
  nombre_masculino: string;
  nombre_femenino: string | null;
}

// ---------- Helpers ----------

async function fetchAllPages<T extends WithId>(
  endpoint: string,
  params: Record<string, string> = {},
): Promise<T[]> {
  let page = 1;
  const acc: T[] = [];
  for (;;) {
    const { data } = await api.get<Paginated<T>>(`/${endpoint}/`, {
      params: { ...params, page: String(page) },
    });
    acc.push(...data.results);
    if (!data.next) break;
    page++;
  }
  return acc;
}

function resolveCargoLabel(
  sexo: "M" | "F" | string,
  execPos: ExecPosition,
): string {
  if (sexo === "M") return execPos.nombre_masculino || "—";
  return execPos.nombre_femenino || execPos.nombre_masculino || "—";
}

// ---------- Page ----------

export default function RepresentantesPage() {
  const user = useAuthStore((s) => s.user);
  const isAdmin = userHasRole(user, "Administrador RENADS");

  const [gobRegId, setGobRegId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [editRow, setEditRow] = useState<Representative | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteRow, setDeleteRow] = useState<Representative | null>(null);

  const queryClient = useQueryClient();

  // Organ directories for selected GR
  const orgDirQuery = useQuery({
    queryKey: ["organ-directories", "by-gr", gobRegId],
    queryFn: () =>
      fetchAllPages<OrgDirectory>("organ-directories", {
        gobierno_regional: String(gobRegId!),
      }),
    enabled: gobRegId != null,
    staleTime: 5 * 60_000,
  });

  // All executive positions — for gendered label lookup
  const execPosQuery = useQuery({
    queryKey: ["executive-positions", "all-lookup"],
    queryFn: () => fetchAllPages<ExecPosition>("executive-positions"),
    staleTime: 10 * 60_000,
  });

  const orgDirMap = useMemo(() => {
    const m = new Map<number, OrgDirectory>();
    for (const d of orgDirQuery.data ?? []) m.set(d.id, d);
    return m;
  }, [orgDirQuery.data]);

  const execPosMap = useMemo(() => {
    const m = new Map<number, ExecPosition>();
    for (const p of execPosQuery.data ?? []) m.set(p.id, p);
    return m;
  }, [execPosQuery.data]);

  const orgDirIds = useMemo(
    () => (orgDirQuery.data ?? []).map((d) => d.id),
    [orgDirQuery.data],
  );

  // Parallel fetch: representatives per organ directory
  const repQueries = useQueries({
    queries: orgDirIds.map((id) => ({
      queryKey: ["organ-representatives", "by-orgdir", id] as const,
      queryFn: () =>
        fetchAllPages<Representative>("organ-representatives", {
          organo_directorio: String(id),
        }),
      staleTime: 0,
      enabled: gobRegId != null,
    })),
  });

  const allReps = useMemo(
    () => repQueries.flatMap((q) => q.data ?? []),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(repQueries.map((q) => q.dataUpdatedAt))],
  );

  const isLoadingReps =
    gobRegId != null &&
    (orgDirQuery.isLoading || repQueries.some((q) => q.isLoading));

  const filteredReps = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return allReps;
    return allReps.filter(
      (r) =>
        r.nombre.toLowerCase().includes(q) ||
        r.numero_documento_identidad.toLowerCase().includes(q),
    );
  }, [allReps, search]);

  const invalidateReps = () =>
    queryClient.invalidateQueries({
      queryKey: ["organ-representatives", "by-orgdir"],
    });

  // Delete
  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/organ-representatives/${id}/`);
    },
    onSuccess() {
      toast.success("Representante eliminado.");
      setDeleteRow(null);
      invalidateReps();
    },
    onError(err) {
      toast.error(extractApiError(err));
      setDeleteRow(null);
    },
  });

  return (
    <div className="grid gap-6">
      <Link
        href="/catalogos"
        className="text-sm text-muted-foreground hover:text-foreground w-fit"
      >
        ← Catálogos
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-semibold">
            Autoridades Representantes por Entidad
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Selecciona un gobierno regional para gestionar sus representantes.
          </p>
        </div>
        {gobRegId != null && isAdmin && (
          <Button
            size="sm"
            onClick={() => {
              setEditRow(null);
              setDialogOpen(true);
            }}
          >
            <Plus className="h-4 w-4" />
            Nuevo representante
          </Button>
        )}
      </div>

      {/* GR selector */}
      <div className="grid gap-1.5 max-w-md">
        <label className="text-sm font-medium flex items-center gap-2">
          <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-semibold">
            1
          </span>
          Gobierno Regional
        </label>
        <EntityCombobox
          endpoint="regional-governments"
          value={gobRegId}
          onChange={(id) => {
            setGobRegId(id);
            setSearch("");
          }}
          placeholder="Buscar gobierno regional…"
          toLabel={(r) => String(r.nombre ?? r.id)}
        />
      </div>

      {/* Table area */}
      {!gobRegId ? (
        <EmptyState />
      ) : isLoadingReps ? (
        <TableSkeleton />
      ) : (
        <div className="grid gap-4">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground pointer-events-none" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar por nombre o N° documento…"
                className="pl-8"
              />
            </div>
            <Badge variant="secondary" className="shrink-0 tabular-nums">
              {filteredReps.length}{" "}
              {filteredReps.length !== 1 ? "representantes" : "representante"}
            </Badge>
          </div>

          <div className="rounded-lg border overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="text-left font-medium text-muted-foreground px-4 py-3">
                    Órgano del directorio
                  </th>
                  <th className="text-left font-medium text-muted-foreground px-4 py-3">
                    Representante
                  </th>
                  <th className="text-left font-medium text-muted-foreground px-4 py-3">
                    Cargo
                  </th>
                  <th className="text-left font-medium text-muted-foreground px-4 py-3">
                    Fecha de designación
                  </th>
                  <th className="text-left font-medium text-muted-foreground px-4 py-3">
                    N° resolución
                  </th>
                  {isAdmin && <th className="w-28 px-4 py-3" />}
                </tr>
              </thead>
              <tbody>
                {filteredReps.length === 0 ? (
                  <tr>
                    <td
                      colSpan={isAdmin ? 6 : 5}
                      className="text-center text-muted-foreground py-12"
                    >
                      {search
                        ? "No hay representantes que coincidan con la búsqueda."
                        : "No hay representantes registrados para este gobierno regional."}
                    </td>
                  </tr>
                ) : (
                  filteredReps.map((rep) => {
                    const orgDir = orgDirMap.get(rep.organo_directorio);
                    const execPos = execPosMap.get(rep.cargo_ejecutivo);
                    const cargo = execPos
                      ? resolveCargoLabel(rep.sexo, execPos)
                      : `#${rep.cargo_ejecutivo}`;
                    return (
                      <tr
                        key={rep.id}
                        className="border-b last:border-0 hover:bg-muted/30 transition-colors"
                      >
                        <td className="px-4 py-3 text-muted-foreground">
                          {orgDir?.nombre ?? `#${rep.organo_directorio}`}
                        </td>
                        <td className="px-4 py-3 font-medium">{rep.nombre}</td>
                        <td className="px-4 py-3">{cargo}</td>
                        <td className="px-4 py-3 tabular-nums">
                          {rep.fecha_inicio_designacion}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">
                          {rep.numero_resolucion_designacion || "—"}
                        </td>
                        {isAdmin && (
                          <td className="px-4 py-3">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-7 w-7"
                                title="Editar"
                                onClick={() => {
                                  setEditRow(rep);
                                  setDialogOpen(true);
                                }}
                              >
                                <Pencil className="h-3.5 w-3.5" />
                              </Button>
                              <AnnexChecklistAction
                                entidad="organ-representatives"
                                row={rep}
                              />
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                                title="Eliminar"
                                onClick={() => setDeleteRow(rep)}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          </td>
                        )}
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Create/Edit dialog */}
      <RepresentativeDialog
        open={dialogOpen}
        row={editRow}
        gobRegId={gobRegId}
        onClose={() => {
          setDialogOpen(false);
          setEditRow(null);
        }}
        onSuccess={() => {
          setDialogOpen(false);
          setEditRow(null);
          invalidateReps();
        }}
      />

      {/* Delete confirmation */}
      <AlertDialog
        open={deleteRow != null}
        onOpenChange={(o) => {
          if (!o) setDeleteRow(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar representante?</AlertDialogTitle>
            <AlertDialogDescription>
              Se eliminará a <strong>{deleteRow?.nombre}</strong>. Esta acción
              no se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteRow && deleteMutation.mutate(deleteRow.id)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Eliminar"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// ---------- Create / Edit dialog ----------

interface RepFormValues {
  nombre: string;
  tipo_documento_identidad: number | null;
  numero_documento_identidad: string;
  sexo: "M" | "F" | "";
  organo_directorio: number | null;
  cargo_ejecutivo: number | null;
  fecha_inicio_designacion: string;
  numero_resolucion_designacion: string;
  fecha_inicio_facultades: string;
  activo: boolean;
}

function RepresentativeDialog({
  open,
  row,
  gobRegId,
  onClose,
  onSuccess,
}: {
  open: boolean;
  row: Representative | null;
  gobRegId: number | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const isEdit = row != null;

  const { control, handleSubmit, reset, setValue } = useForm<RepFormValues>({
    defaultValues: {
      nombre: "",
      tipo_documento_identidad: null,
      numero_documento_identidad: "",
      sexo: "",
      organo_directorio: null,
      cargo_ejecutivo: null,
      fecha_inicio_designacion: "",
      numero_resolucion_designacion: "",
      fecha_inicio_facultades: "",
      activo: true,
    },
  });

  const sexo = useWatch({ control, name: "sexo" }) as "M" | "F" | "";
  const orgDirId = useWatch({ control, name: "organo_directorio" });

  // Fetch cargos ejecutivos for the selected organ directory.
  // executive-positions now FK directly to organ-directories via organo_directivo.
  const { data: dirPositions, isLoading: positionsLoading } = useQuery({
    queryKey: ["executive-positions", "by-orgdir", orgDirId],
    queryFn: () =>
      fetchAllPages<{
        id: number;
        nombre_masculino: string;
        nombre_femenino: string | null;
      }>("executive-positions", {
        organo_directivo: String(orgDirId!),
        activo: "true",
      }),
    enabled: !!orgDirId,
    staleTime: 2 * 60_000,
  });

  const cargoOptions = useMemo(() => {
    if (!dirPositions) return [];
    return dirPositions.map((p) => ({
      id: p.id,
      nombre_masculino: p.nombre_masculino,
      nombre_femenino: p.nombre_femenino,
    }));
  }, [dirPositions]);

  // Reset form when dialog opens
  useEffect(() => {
    if (!open) return;
    if (row) {
      reset({
        nombre: row.nombre,
        tipo_documento_identidad: row.tipo_documento_identidad,
        numero_documento_identidad: row.numero_documento_identidad,
        sexo: row.sexo,
        organo_directorio: row.organo_directorio,
        cargo_ejecutivo: row.cargo_ejecutivo,
        fecha_inicio_designacion: row.fecha_inicio_designacion,
        numero_resolucion_designacion: row.numero_resolucion_designacion ?? "",
        fecha_inicio_facultades: row.fecha_inicio_facultades ?? "",
        activo: row.activo,
      });
    } else {
      reset({
        nombre: "",
        tipo_documento_identidad: null,
        numero_documento_identidad: "",
        sexo: "",
        organo_directorio: null,
        cargo_ejecutivo: null,
        fecha_inicio_designacion: "",
        numero_resolucion_designacion: "",
        fecha_inicio_facultades: "",
        activo: true,
      });
    }
  }, [open, row, reset]);

  const saveMutation = useMutation({
    mutationFn: async (values: RepFormValues) => {
      const payload = {
        nombre: values.nombre,
        tipo_documento_identidad: values.tipo_documento_identidad,
        numero_documento_identidad: values.numero_documento_identidad,
        sexo: values.sexo,
        organo_directorio: values.organo_directorio,
        cargo_ejecutivo: values.cargo_ejecutivo,
        fecha_inicio_designacion: values.fecha_inicio_designacion,
        numero_resolucion_designacion:
          values.numero_resolucion_designacion || null,
        fecha_inicio_facultades: values.fecha_inicio_facultades || null,
        activo: values.activo,
      };
      if (isEdit) {
        await api.patch(`/organ-representatives/${row!.id}/`, payload);
      } else {
        await api.post(`/organ-representatives/`, payload);
      }
    },
    onSuccess() {
      toast.success(
        isEdit ? "Representante actualizado." : "Representante registrado.",
      );
      onSuccess();
    },
    onError(err) {
      toast.error(extractApiError(err));
    },
  });

  // Show codigo (abbreviation) for identity document types
  const docTypeLabel = (r: WithId) => {
    const row = r as { codigo?: string; nombre?: string };
    return row.codigo ?? row.nombre ?? String(r.id);
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Editar representante" : "Nuevo representante"}
          </DialogTitle>
        </DialogHeader>

        <form
          onSubmit={handleSubmit((v) => saveMutation.mutate(v))}
          className="grid gap-3 px-1 pb-1"
        >
          {/* ── Datos personales ── */}
          <SectionHeader label="Datos personales" />

          {/* Nombre */}
          <Controller
            control={control}
            name="nombre"
            rules={{ required: "Campo obligatorio." }}
            render={({ field, fieldState }) => (
              <div className="grid gap-1">
                <Label>Nombre completo *</Label>
                <Input value={field.value} onChange={field.onChange} onBlur={field.onBlur} autoComplete="off" />
                {fieldState.error && <p className="text-xs text-destructive">{fieldState.error.message}</p>}
              </div>
            )}
          />

          {/* Tipo doc | N° doc | Sexo — 3 cols */}
          <div className="grid grid-cols-3 gap-3">
            <Controller
              control={control}
              name="tipo_documento_identidad"
              rules={{ required: "Campo obligatorio." }}
              render={({ field, fieldState }) => (
                <div className="grid gap-1">
                  <Label>Tipo documento *</Label>
                  <EntityCombobox endpoint="identity-document-types" value={field.value} onChange={field.onChange} toLabel={docTypeLabel} />
                  {fieldState.error && <p className="text-xs text-destructive">{fieldState.error.message}</p>}
                </div>
              )}
            />
            <Controller
              control={control}
              name="numero_documento_identidad"
              rules={{ required: "Campo obligatorio." }}
              render={({ field, fieldState }) => (
                <div className="grid gap-1">
                  <Label>N° documento *</Label>
                  <Input value={field.value} onChange={field.onChange} onBlur={field.onBlur} autoComplete="off" />
                  {fieldState.error && <p className="text-xs text-destructive">{fieldState.error.message}</p>}
                </div>
              )}
            />
            <Controller
              control={control}
              name="sexo"
              rules={{ required: "Campo obligatorio." }}
              render={({ field, fieldState }) => (
                <div className="grid gap-1">
                  <Label>Sexo *</Label>
                  <Select
                    value={field.value}
                    onValueChange={(v) => {
                      field.onChange(v);
                      setValue("cargo_ejecutivo", null);
                    }}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Seleccionar…" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="M">Masculino</SelectItem>
                      <SelectItem value="F">Femenino</SelectItem>
                    </SelectContent>
                  </Select>
                  {fieldState.error && <p className="text-xs text-destructive">{fieldState.error.message}</p>}
                </div>
              )}
            />
          </div>

          {/* ── Designación ── */}
          <SectionHeader label="Designación" />

          {/* Órgano | Cargo — 2 cols; cargo bloqueado hasta elegir sexo */}
          <div className="grid grid-cols-2 gap-3">
            <Controller
              control={control}
              name="organo_directorio"
              rules={{ required: "Campo obligatorio." }}
              render={({ field, fieldState }) => (
                <div className="grid gap-1">
                  <Label>Órgano del directorio *</Label>
                  <EntityCombobox
                    endpoint="organ-directories"
                    params={gobRegId ? { gobierno_regional: String(gobRegId) } : undefined}
                    value={field.value}
                    onChange={(id) => {
                      if (id !== field.value) setValue("cargo_ejecutivo", null);
                      field.onChange(id);
                    }}
                  />
                  {fieldState.error && <p className="text-xs text-destructive">{fieldState.error.message}</p>}
                </div>
              )}
            />
            <Controller
              control={control}
              name="cargo_ejecutivo"
              rules={{ required: "Campo obligatorio." }}
              render={({ field, fieldState }) => {
                const disabled = !sexo || !orgDirId;
                const hint = !sexo
                  ? "— elige sexo primero"
                  : !orgDirId
                    ? "— elige órgano primero"
                    : undefined;
                const selectedLabel = (() => {
                  const opt = cargoOptions.find((o) => o.id === field.value);
                  if (!opt) return undefined;
                  return sexo === "M"
                    ? opt.nombre_masculino
                    : (opt.nombre_femenino ?? opt.nombre_masculino);
                })();
                return (
                  <div className="grid gap-1">
                    <Label>
                      Cargo ejecutivo *{" "}
                      {hint && (
                        <span className="text-xs text-amber-600 font-normal">{hint}</span>
                      )}
                    </Label>
                    <Select
                      value={field.value ? String(field.value) : ""}
                      onValueChange={(v) => field.onChange(v ? Number(v) : null)}
                      disabled={disabled}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue
                          placeholder={
                            positionsLoading
                              ? "Cargando cargos…"
                              : cargoOptions.length === 0 && orgDirId
                                ? "Sin cargos configurados"
                                : "Seleccionar cargo…"
                          }
                        >
                          {selectedLabel}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {cargoOptions.length === 0 && !positionsLoading && orgDirId && (
                          <div className="px-3 py-4 text-xs text-muted-foreground text-center">
                            No hay cargos configurados para este órgano.
                            <br />
                            Configure en Catálogos → Cargos ejecutivos.
                          </div>
                        )}
                        {cargoOptions.map((opt) => (
                          <SelectItem key={opt.id} value={String(opt.id)}>
                            {sexo === "M"
                              ? opt.nombre_masculino
                              : (opt.nombre_femenino ?? opt.nombre_masculino)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {fieldState.error && (
                      <p className="text-xs text-destructive">{fieldState.error.message}</p>
                    )}
                  </div>
                );
              }}
            />
          </div>

          {/* Fecha designación | N° resolución | Fecha facultades — 3 cols */}
          <div className="grid grid-cols-3 gap-3">
            <Controller
              control={control}
              name="fecha_inicio_designacion"
              rules={{ required: "Campo obligatorio." }}
              render={({ field, fieldState }) => (
                <div className="grid gap-1">
                  <Label>Fecha de designación *</Label>
                  <DatePicker value={field.value} onChange={field.onChange} />
                  {fieldState.error && <p className="text-xs text-destructive">{fieldState.error.message}</p>}
                </div>
              )}
            />
            <Controller
              control={control}
              name="numero_resolucion_designacion"
              render={({ field }) => (
                <div className="grid gap-1">
                  <Label>N° resolución</Label>
                  <Input value={field.value} onChange={field.onChange} onBlur={field.onBlur} autoComplete="off" />
                </div>
              )}
            />
            <Controller
              control={control}
              name="fecha_inicio_facultades"
              render={({ field }) => (
                <div className="grid gap-1">
                  <Label>Fecha inicio de facultades</Label>
                  <DatePicker value={field.value} onChange={field.onChange} />
                </div>
              )}
            />
          </div>

          {/* ── Estado ── */}
          <SectionHeader label="Estado" />

          <Controller
            control={control}
            name="activo"
            render={({ field }) => (
              <div className="flex items-center justify-between gap-2">
                <Label>Activo</Label>
                <Switch checked={Boolean(field.value)} onCheckedChange={field.onChange} />
              </div>
            )}
          />

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="outline" onClick={onClose}>Cancelar</Button>
            <Button type="submit" disabled={saveMutation.isPending}>
              {saveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Guardar"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ---------- Sub-components ----------

function SectionHeader({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 pt-1">
      <span className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        {label}
      </span>
      <div className="flex-1 border-t" />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 gap-3 text-center">
      <Building2 className="h-10 w-10 text-muted-foreground/40" />
      <p className="text-sm font-medium text-muted-foreground">
        Selecciona un gobierno regional para continuar
      </p>
      <p className="text-xs text-muted-foreground/60 max-w-xs">
        Los representantes se gestionan por entidad dentro de cada gobierno
        regional.
      </p>
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="rounded-lg border overflow-hidden">
      <div className="bg-muted/50 px-4 py-3 border-b flex gap-6">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-4 w-24" />
        ))}
      </div>
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-6 px-4 py-3.5 border-b last:border-0"
        >
          <Skeleton className="h-4 w-36" />
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-20" />
        </div>
      ))}
    </div>
  );
}
