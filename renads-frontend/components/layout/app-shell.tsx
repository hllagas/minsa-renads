"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useAuthStore, userHasRole, type AuthUser } from "@/lib/auth/store";
import { useLogout } from "@/lib/auth/hooks";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

/** Ítem de navegación. `roles` vacío = visible para cualquier usuario autenticado. */
interface NavItem {
  href: string;
  label: string;
  roles: string[];
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Inicio", roles: [] },
  { href: "/convenios", label: "Convenios", roles: ["Administrador RENADS", "DIGEP", "CONAPRES", "OGAJ", "Secretaría General"] },
  { href: "/internados", label: "Internados", roles: ["Administrador RENADS", "Universidad", "Autoridad de convenio"] },
  { href: "/actividades", label: "Actividades", roles: ["Administrador RENADS", "Universidad", "Tutor", "Sede docente"] },
];

function iniciales(nombre: string): string {
  return nombre
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

function visibleParaUsuario(item: NavItem, user: AuthUser | null): boolean {
  return item.roles.length === 0 || userHasRole(user, ...item.roles);
}

export function AppShell({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const pathname = usePathname();
  const logout = useLogout();

  const items = NAV_ITEMS.filter((item) => visibleParaUsuario(item, user));

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 border-r bg-muted/30 p-4 md:block">
        <div className="mb-6 px-2 text-lg font-semibold">RENADS</div>
        <nav className="grid gap-1">
          {items.map((item) => {
            const active =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-md px-3 py-2 text-sm transition-colors",
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center justify-end border-b px-4">
          <DropdownMenu>
            <DropdownMenuTrigger render={<Button variant="ghost" className="gap-2 px-2" />}>
              <Avatar className="size-7">
                <AvatarFallback>{iniciales(user?.nombre ?? "?")}</AvatarFallback>
              </Avatar>
              <span className="hidden text-sm sm:inline">{user?.nombre}</span>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuGroup>
                <DropdownMenuLabel>
                  <div className="font-medium">{user?.nombre}</div>
                  <div className="text-xs text-muted-foreground">
                    {user?.grupos.join(", ") || "Sin roles"}
                  </div>
                </DropdownMenuLabel>
              </DropdownMenuGroup>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout}>Cerrar sesión</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
