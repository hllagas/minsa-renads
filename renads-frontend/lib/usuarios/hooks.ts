"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { setUserPassword } from "@/lib/api/users";
import { resourceKeys } from "@/lib/api/query";

/**
 * Mutación para cambiar la contraseña de un usuario (acción `set-password`). Invalida la lista de
 * usuarios al tener éxito. La contraseña no se persiste en estado de cliente ni se cachea.
 */
export function useSetPassword() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, password }: { id: number; password: string }) =>
      setUserPassword(id, password),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: resourceKeys.all("users") }),
  });
}
