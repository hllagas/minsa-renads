"use client";

import { useMemo, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import type { WithId } from "@/lib/api/query";
import { getResourceItem, searchResource } from "@/lib/api/lookup";
import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
} from "@/components/ui/combobox";

export interface ComboboxItemData {
  id: string | number;
  label: string;
}

/**
 * Combobox con **búsqueda server-side** para una FK (catálogo/entidad DRF). Consulta
 * `/{endpoint}/?search=` (SearchFilter del backend), por lo que escala a catálogos grandes
 * (ubigeo, convention-statuses) sin la limitación de una sola página.
 *
 * Resuelve la etiqueta del valor seleccionado aunque no esté en los resultados actuales
 * (consulta el detalle por id), útil al editar.
 *
 * Soporta PK **numérica o textual**: `valueKey` (default `"id"`) indica qué clave del registro
 * es el identificador — p. ej. `"codigo"` (executing-units) o `"codigo_renipress"` (ipress).
 */
export function EntityCombobox<T extends string | number = number>({
  endpoint,
  value,
  onChange,
  toLabel = (row) => String(row.nombre ?? row.titulo ?? row.id),
  params,
  placeholder = "Buscar…",
  disabled,
  valueKey = "id",
}: {
  endpoint: string;
  value: T | null | undefined;
  onChange: (value: T | null) => void;
  toLabel?: (row: WithId) => string;
  params?: Record<string, string>;
  placeholder?: string;
  disabled?: boolean;
  valueKey?: string;
}) {
  const [search, setSearch] = useState("");

  const listQuery = useQuery({
    queryKey: [endpoint, "combobox", params ?? null, search],
    queryFn: () => searchResource(endpoint, { search, params }),
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });

  // Detalle del valor seleccionado (para la etiqueta al editar, si no está en la lista).
  const selectedQuery = useQuery({
    queryKey: [endpoint, "detail", value],
    queryFn: () => getResourceItem(endpoint, value as string | number),
    enabled: value != null,
    staleTime: 5 * 60_000,
  });

  const idOf = (row: WithId): string | number =>
    (row[valueKey] as string | number | undefined) ?? row.id;

  const items = useMemo<ComboboxItemData[]>(() => {
    const rows = listQuery.data ?? [];
    const list = rows.map((r) => ({ id: idOf(r), label: toLabel(r) }));
    if (value != null && selectedQuery.data && !list.some((i) => i.id === value)) {
      list.unshift({ id: idOf(selectedQuery.data), label: toLabel(selectedQuery.data) });
    }
    return list;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listQuery.data, selectedQuery.data, value, valueKey]);

  const selectedItem = items.find((i) => i.id === value) ?? null;

  return (
    <Combobox
      items={items}
      value={selectedItem}
      onValueChange={(item: ComboboxItemData | null) => onChange(item ? (item.id as T) : null)}
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
          {items.map((item) => (
            <ComboboxItem key={item.id} value={item}>
              {item.label}
            </ComboboxItem>
          ))}
        </ComboboxList>
      </ComboboxContent>
    </Combobox>
  );
}
