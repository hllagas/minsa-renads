import { useEffect, useState } from "react";

/**
 * Devuelve una versión retrasada de `value` que solo se actualiza tras `delay` ms sin cambios.
 * Útil para no disparar una petición por cada tecla en buscadores.
 */
export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);

  return debounced;
}
