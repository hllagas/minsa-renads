"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useSyncExternalStore } from "react";

import {
  changePassword,
  fetchMe,
  isTwoFactorPending,
  login,
  verify2fa,
  type ChangePasswordPayload,
  type LoginCredentials,
  type TwoFactorVerifyPayload,
} from "@/lib/api/auth";
import { useAuthStore } from "@/lib/auth/store";

/** Query key del usuario actual. */
export const meQueryKey = ["auth", "me"] as const;

/**
 * ¿Terminó `zustand/persist` de rehidratar la sesión desde `localStorage`?
 * En SSR devuelve `false` (snapshot de servidor), evitando el mismatch de hidratación; en cliente
 * refleja `persist.hasHydrated()` y se actualiza al terminar. Los guards deben esperar esto antes de
 * redirigir por falta de token: en una recarga (F5) de una URL profunda el token llega de forma
 * asíncrona, y sin esta espera el guard rebotaría a `/login` (y de ahí a `/inicio`).
 */
export function useAuthHydrated(): boolean {
  return useSyncExternalStore(
    (onChange) => useAuthStore.persist.onFinishHydration(onChange),
    () => useAuthStore.persist.hasHydrated(),
    () => false,
  );
}

/**
 * Login: obtiene tokens, los guarda en el store y precarga `me`.
 * La UI usa `mutate`/`isPending`/`error`.
 */
export function useLogin() {
  const setTokens = useAuthStore((s) => s.setTokens);
  const setPendingTwoFactor = useAuthStore((s) => s.setPendingTwoFactor);
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (credentials: LoginCredentials) => login(credentials),
    onSuccess: async (response) => {
      if (isTwoFactorPending(response)) {
        setPendingTwoFactor({ sessionToken: response.session_token, method: response.method });
        router.replace("/login/2fa");
        return;
      }
      setTokens(response.access, response.refresh);
      await queryClient.invalidateQueries({ queryKey: meQueryKey });
      router.replace("/inicio");
    },
  });
}

export function useVerify2fa() {
  const setTokens = useAuthStore((s) => s.setTokens);
  const setPendingTwoFactor = useAuthStore((s) => s.setPendingTwoFactor);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: TwoFactorVerifyPayload) => verify2fa(payload),
    onSuccess: async (tokens) => {
      setPendingTwoFactor(null);
      setTokens(tokens.access, tokens.refresh);
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

/**
 * Cambia la propia contraseña (RN-22). Al éxito hidrata `store.user` con el `me` devuelto
 * (ya con `debe_cambiar_password=false`) e invalida la query de `me`.
 */
export function useChangePassword() {
  const setUser = useAuthStore((s) => s.setUser);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ChangePasswordPayload) => changePassword(payload),
    onSuccess: (user) => {
      setUser(user);
      queryClient.setQueryData(meQueryKey, user);
    },
  });
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
