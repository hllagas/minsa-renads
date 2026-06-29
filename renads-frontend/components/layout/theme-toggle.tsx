"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { MoonIcon, SunIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

/**
 * Botón para alternar entre modo claro y oscuro en tiempo real.
 * Usa next-themes (atributo `class` sobre <html>). El guard `mounted`
 * evita el desajuste de hidratación: el tema real solo se conoce en cliente.
 */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const isDark = resolvedTheme === "dark";

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      aria-label={isDark ? "Activar modo claro" : "Activar modo oscuro"}
      title={isDark ? "Modo claro" : "Modo oscuro"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
    >
      {/* Antes de montar, render neutro para que SSR y cliente coincidan. */}
      {mounted ? (
        isDark ? (
          <SunIcon />
        ) : (
          <MoonIcon />
        )
      ) : (
        <SunIcon className="opacity-0" />
      )}
    </Button>
  );
}
