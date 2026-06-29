"use client";

import { useMemo, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { XIcon } from "lucide-react";

import type { WithId } from "@/lib/api/query";
import { getResourceItem, searchResource } from "@/lib/api/lookup";
import { Badge } from "@/components/ui/badge";
import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
} from "@/components/ui/combobox";

interface ComboboxItemData {
  id: number;
  label: string;
}

const defaultToLabel = (row: WithId) =>
  String(row.nombre ?? row.titulo ?? row.name ?? row.id);

/**
 * Selector **múltiple** de una FK (catálogo/entidad DRF) con **búsqueda server-side**. El valor es
 * `number[]` (ids). Escala a catálogos grandes (`permissions`) sin cargar todo: busca por
 * `/{endpoint}/?search=` y resuelve por id las etiquetas de los seleccionados que no estén en la
 * página actual (`getResourceItem`). Compone el `Combobox` base como control de "añadir"; los
 * elementos elegidos se muestran como badges removibles. No reinventa el combobox base.
 */
export function MultiEntityCombobox({
  endpoint,
  value,
  onChange,
  toLabel = defaultToLabel,
  params,
  placeholder = "Buscar…",
  disabled,
}: {
  endpoint: string;
  value: number[];
  onChange: (value: number[]) => void;
  toLabel?: (row: WithId) => string;
  params?: Record<string, string>;
  placeholder?: string;
  disabled?: boolean;
}) {
  const [search, setSearch] = useState("");

  const listQuery = useQuery({
    queryKey: [endpoint, "multi-combobox", params ?? null, search],
    queryFn: () => searchResource(endpoint, { search, params }),
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });

  // Resuelve las etiquetas de los ids seleccionados (incluso los ausentes de la búsqueda actual).
  const selectedQuery = useQuery({
    queryKey: [endpoint, "multi-detail", value],
    queryFn: () => Promise.all(value.map((id) => getResourceItem(endpoint, id))),
    enabled: value.length > 0,
    staleTime: 5 * 60_000,
  });

  const labelById = useMemo(() => {
    const map = new Map<number, string>();
    for (const r of listQuery.data ?? []) map.set(r.id, toLabel(r));
    for (const r of selectedQuery.data ?? []) map.set(r.id, toLabel(r));
    return map;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listQuery.data, selectedQuery.data]);

  // Candidatos = resultados de búsqueda menos lo ya seleccionado (evita duplicados).
  const candidates = useMemo<ComboboxItemData[]>(
    () =>
      (listQuery.data ?? [])
        .filter((r) => !value.includes(r.id))
        .map((r) => ({ id: r.id, label: toLabel(r) })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [listQuery.data, value],
  );

  function add(id: number) {
    if (!value.includes(id)) onChange([...value, id]);
  }

  function remove(id: number) {
    onChange(value.filter((v) => v !== id));
  }

  return (
    <div className="grid gap-2">
      <Combobox
        items={candidates}
        value={null}
        onValueChange={(item: ComboboxItemData | null) => {
          if (item) add(item.id);
        }}
        onInputValueChange={(text: string) => setSearch(text)}
        itemToStringLabel={(item: ComboboxItemData) => item.label}
        itemToStringValue={(item: ComboboxItemData) => String(item.id)}
        isItemEqualToValue={(a: ComboboxItemData, b: ComboboxItemData) => a.id === b.id}
        filter={null}
        disabled={disabled}
      >
        <ComboboxInput placeholder={placeholder} className="w-full" />
        <ComboboxContent>
          <ComboboxEmpty>
            {listQuery.isFetching ? "Buscando…" : "Sin resultados."}
          </ComboboxEmpty>
          <ComboboxList>
            {candidates.map((item) => (
              <ComboboxItem key={item.id} value={item}>
                {item.label}
              </ComboboxItem>
            ))}
          </ComboboxList>
        </ComboboxContent>
      </Combobox>

      {value.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {value.map((id) => (
            <Badge key={id} variant="secondary" className="gap-1 pr-1">
              <span className="truncate">{labelById.get(id) ?? `#${id}`}</span>
              <button
                type="button"
                onClick={() => remove(id)}
                disabled={disabled}
                aria-label={`Quitar ${labelById.get(id) ?? id}`}
                className="rounded-sm opacity-60 transition-opacity hover:opacity-100 disabled:pointer-events-none"
              >
                <XIcon className="size-3" />
              </button>
            </Badge>
          ))}
        </div>
      ) : null}
    </div>
  );
}
