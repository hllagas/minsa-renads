"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { fetchMe, login, type LoginCredentials } from "@/lib/api/auth";
import { useAuthStore } from "@/lib/auth/store";

/** Query key del usuario actual. */
export const meQueryKey = ["auth", "me"] as const;

/**
 * Login: obtiene tokens, los guarda en el store y precarga `me`.
 * La UI usa `mutate`/`isPending`/`error`.
 */
export function useLogin() {
  const setTokens = useAuthStore((s) => s.setTokens);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (credentials: LoginCredentials) => login(credentials),
    onSuccess: async (tokens) => {
      setTokens(tokens.access, tokens.refresh);
      // Con el token ya en el store, carga el usuario.
      await queryClient.invalidateQueries({ queryKey: meQueryKey });
    },
  });
}

/**
 * Usuario autenticado (`/auth/me/`). Solo se ejecuta si hay access token.
 * Hidrata `store.user` al resolver para el gating por rol.
 */
export function useMe() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const setUser = useAuthStore((s) => s.setUser);

  const query = useQuery({
    queryKey: meQueryKey,
    queryFn: fetchMe,
    enabled: !!accessToken,
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    if (query.data) setUser(query.data);
  }, [query.data, setUser]);

  return query;
}

/** Logout: limpia sesión y cache, redirige a /login. */
export function useLogout() {
  const clear = useAuthStore((s) => s.clear);
  const queryClient = useQueryClient();
  const router = useRouter();

  return () => {
    clear();
    queryClient.clear();
    router.replace("/login");
  };
}
