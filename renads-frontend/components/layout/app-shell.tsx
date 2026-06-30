"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { LogOutIcon, MenuIcon, UserIcon } from "lucide-react";

import { useAuthStore, userHasRole, type AuthUser } from "@/lib/auth/store";
import { useLogout } from "@/lib/auth/hooks";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Footer } from "@/components/layout/footer";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
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
  { href: "/inicio", label: "Inicio", roles: [] },
  { href: "/dashboard", label: "Dashboard", roles: [] },
  { href: "/convenios", label: "Convenios", roles: ["Administrador RENADS", "DIGEP", "CONAPRES", "OGAJ", "Secretaría General"] },
  { href: "/internados", label: "Internados", roles: ["Administrador RENADS", "Universidad", "Autoridad de convenio"] },
  { href: "/actividades", label: "Actividades", roles: ["Administrador RENADS", "Universidad", "Tutor", "Sede docente"] },
  { href: "/catalogos", label: "Catálogos", roles: ["Administrador RENADS", "Auditor"] },
  { href: "/usuarios", label: "Gestión de Usuarios", roles: ["Administrador RENADS"] },
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

/** Lista de enlaces de navegación, reutilizada por la barra lateral (desktop) y el drawer (móvil). */
function NavLinks({
  items,
  pathname,
  onNavigate,
}: {
  items: NavItem[];
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <nav className="grid gap-1">
      {items.map((item) => {
        const active =
          item.href === "/inicio" ? pathname === "/inicio" : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
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
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const pathname = usePathname();
  const logout = useLogout();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  // Glassmorphism sutil: al hacer scroll, el navbar pasa a navy translúcido + blur.
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const items = NAV_ITEMS.filter((item) => visibleParaUsuario(item, user));

  return (
    <div className="flex min-h-dvh flex-col">
      {/* Navbar full width, siempre visible (sticky) sobre toda la app */}
      <header
          className={cn(
            "sticky top-0 z-40 flex h-14 items-center gap-2 px-4 text-white transition-colors",
            scrolled
              ? "border-b border-white/10 bg-navy/75 backdrop-blur-sm supports-[backdrop-filter]:bg-navy/65"
              : "border-b border-transparent bg-navy",
          )}
        >
          {/* Hamburguesa + drawer solo en móvil */}
          <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
            <SheetTrigger
              render={
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="md:hidden"
                  aria-label="Abrir navegación"
                />
              }
            >
              <MenuIcon />
            </SheetTrigger>
            <SheetContent side="left">
              <SheetHeader>
                <Image
                  src="/logo-minsa.png"
                  alt="Ministerio de Salud del Perú"
                  width={2000}
                  height={408}
                  className="h-8 w-auto"
                />
                <SheetTitle>RENADS</SheetTitle>
              </SheetHeader>
              <NavLinks
                items={items}
                pathname={pathname}
                onNavigate={() => setMobileNavOpen(false)}
              />
            </SheetContent>
          </Sheet>

          {/* Logo visible en móvil (en desktop ya está en la barra lateral) */}
          <Image
            src="/logo-minsa.png"
            alt="Ministerio de Salud del Perú"
            width={2000}
            height={408}
            priority
            className="h-7 w-auto md:hidden"
          />

          {/* Título del proyecto, centrado. Completo en web; en móvil solo "RENADS". */}
          <span
            title="Registro Nacional de Articulación Docencia-Servicio en Salud - RENADS"
            className="absolute left-1/2 max-w-[60%] -translate-x-1/2 truncate text-center font-bold text-white"
          >
            <span className="text-base lg:hidden">RENADS</span>
            <span className="hidden text-lg lg:inline">
              Registro Nacional de Articulación Docencia-Servicio en Salud - RENADS
            </span>
          </span>
          <div className="ml-auto flex items-center gap-1 [&_button:hover]:bg-white/10">
            <ThemeToggle />
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
                <DropdownMenuItem render={<Link href="/perfil" />}>
                  <UserIcon />
                  Perfil
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive" onClick={logout}>
                  <LogOutIcon />
                  Cerrar sesión
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
      </header>

      <div className="flex flex-1">
        {/* Barra lateral siempre visible (sticky bajo el navbar) en desktop */}
        <aside className="sticky top-14 hidden h-[calc(100dvh-3.5rem)] w-60 shrink-0 self-start overflow-y-auto border-r bg-muted/30 p-4 md:block">
          <div className="mb-6 px-2">
            <Image
              src="/logo-minsa.png"
              alt="Ministerio de Salud del Perú"
              width={2000}
              height={408}
              priority
              className="h-8 w-auto"
            />
          </div>
          <NavLinks items={items} pathname={pathname} />
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <main className="flex-1 p-4 sm:p-6">{children}</main>
          <Footer />
        </div>
      </div>
    </div>
  );
}
