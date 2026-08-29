"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { useAuthStore } from "@/lib/auth/store";
import { useAuthHydrated, useMe } from "@/lib/auth/hooks";
import { AppShell } from "@/components/layout/app-shell";
import { ChangePasswordGate } from "@/components/auth/change-password-gate";

/**
 * Layout autenticado. Guard del lado del cliente: sin token redirige a /login.
 * Con token, carga `me`; si la sesión es inválida (refresh falló → token limpiado),
 * el guard redirige. Mientras carga el usuario, muestra estado de carga.
 *
 * Espera a que `zustand/persist` rehidrate (`hydrated`) antes de redirigir: en una recarga (F5)
 * de una URL profunda el token se restaura de forma asíncrona; redirigir antes rebotaría a
 * `/login` (y de ahí a `/inicio`), perdiendo la ruta.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const hydrated = useAuthHydrated();
  const { isLoading, isError } = useMe();

  useEffect(() => {
    if (hydrated && !accessToken) router.replace("/login");
  }, [hydrated, accessToken, router]);

  // Antes de rehidratar no se sabe si hay sesión: mostrar carga (no redirigir).
  if (!hydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Cargando…
      </div>
    );
  }

  if (!accessToken) return null;

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Cargando…
      </div>
    );
  }

  // Token presente pero `me` falló por causa distinta a 401 (el interceptor ya intentó refresh).
  if (isError) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-2 text-sm">
        <p className="text-muted-foreground">No se pudo cargar la sesión.</p>
        <button className="underline" onClick={() => router.replace("/login")}>
          Volver a iniciar sesión
        </button>
      </div>
    );
  }

  return (
    <AppShell>
      <ChangePasswordGate />
      {children}
    </AppShell>
  );
}
