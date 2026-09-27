"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import {
  Building2,
  CalendarDays,
  ChevronRight,
  ClipboardCheck,
  ClipboardList,
  Contact,
  Database,
  FileStack,
  FileText,
  GraduationCap,
  Home,
  Layers,
  LayoutDashboard,
  ListTree,
  LogOutIcon,
  MenuIcon,
  Network,
  ScrollText,
  Share2,
  ShieldCheck,
  Table2,
  Target,
  UserCheck,
  UserIcon,
  Users,
  type LucideIcon,
} from "lucide-react";

import { useAuthStore, userHasRole, type AuthUser } from "@/lib/auth/store";
import { useLogout } from "@/lib/auth/hooks";
import { cn } from "@/lib/utils";
import { CATALOGO_ENTITY_MENU } from "@/lib/catalogos/entities";
import { CATALOG_MENU } from "@/lib/catalogos/catalogs";
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
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

/**
 * Nodo de navegación. Puede ser una hoja (con `href`) o un grupo (con `children`),
 * que se renderiza como acordeón. `roles` vacío = visible para cualquier usuario autenticado.
 */
interface NavNode {
  label: string;
  icon: LucideIcon;
  href?: string;
  roles?: string[];
  children?: NavNode[];
}

/** Iconos por slug de entidad de catálogo (fallback: Table2). */
const ENTITY_ICON: Record<string, LucideIcon> = {
  universities: Building2,
  faculties: Building2,
  "professional-careers": GraduationCap,
  "university-careers": GraduationCap,
  "university-campuses": Building2,
  ipress: Building2,
  "regional-governments": Building2,
  "organic-units": Network,
  "executing-units": Network,
  networks: Network,
  "micro-networks": Network,
  conapres: Building2,
};

const entidadesChildren: NavNode[] = CATALOGO_ENTITY_MENU.map((e) => ({
  label: e.title,
  icon: ENTITY_ICON[e.slug] ?? Table2,
  href: `/catalogos/entidades/${e.slug}`,
}));

const tipologiaChildren: NavNode[] = CATALOG_MENU.map((c) => ({
  label: c.title,
  icon: ListTree,
  href: `/catalogos/listas/${c.slug}`,
}));

const NAV_ITEMS: NavNode[] = [
  { label: "Inicio", icon: Home, href: "/inicio" },
  {
    label: "Dashboard",
    icon: LayoutDashboard,
    href: "/dashboard",
    // `userHasRole` ya incluye al superusuario.
    roles: ["Administrador RENADS"],
  },
  {
    label: "Convenios",
    icon: FileText,
    href: "/convenios",
    roles: ["Administrador RENADS", "DIGEP", "CONAPRES", "OGAJ", "Secretaría General"],
  },
  {
    label: "Internado",
    icon: GraduationCap,
    roles: ["Administrador RENADS", "Universidad", "Autoridad de convenio"],
    children: [
      { label: "Estudiantes", icon: GraduationCap, href: "/internados/personas/students" },
      { label: "Tutores", icon: Users, href: "/internados/personas/tutors" },
      { label: "Coordinadores", icon: UserCheck, href: "/internados/personas/coordinators" },
      { label: "Internos", icon: ClipboardList, href: "/internados/internos" },
    ],
  },
  {
    label: "Actividades",
    icon: ClipboardCheck,
    href: "/actividades",
    roles: ["Administrador RENADS", "Universidad", "Tutor", "Sede docente"],
  },
  {
    label: "Campos de Formación",
    icon: Layers,
    roles: ["Administrador RENADS", "CONAPRES", "Gobierno Regional"],
    children: [
      { label: "Resumen", icon: Layers, href: "/campos-clinicos" },
      { label: "Determinación", icon: Target, href: "/campos-clinicos/registros" },
      { label: "Asignación", icon: Share2, href: "/campos-clinicos/asignaciones" },
    ],
  },
  { label: "Calendario", icon: CalendarDays, href: "/calendario", roles: ["Administrador RENADS"] },
  {
    label: "Catálogos",
    icon: Database,
    roles: ["Administrador RENADS", "Auditor", "CONAPRES"],
    children: [
      { label: "Entidades", icon: Building2, children: entidadesChildren },
      { label: "Representantes", icon: Contact, href: "/catalogos/representantes" },
      { label: "Tipología", icon: ListTree, children: tipologiaChildren },
      { label: "Documentos", icon: FileStack, href: "/catalogos/documentos" },
      {
        label: "Auditoría",
        icon: ScrollText,
        href: "/catalogos/auditoria",
        roles: ["Administrador RENADS", "Auditor"],
      },
    ],
  },
  { label: "Gestión de Usuarios", icon: ShieldCheck, href: "/usuarios", roles: ["Administrador RENADS"] },
];

function iniciales(nombre: string): string {
  return nombre
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

function visibleParaUsuario(node: NavNode, user: AuthUser | null): boolean {
  const roles = node.roles ?? [];
  return roles.length === 0 || userHasRole(user, ...roles);
}

/** Filtra el árbol de navegación por rol, podando grupos que queden sin hijos visibles. */
function filtrarNav(nodes: NavNode[], user: AuthUser | null): NavNode[] {
  return nodes
    .filter((n) => visibleParaUsuario(n, user))
    .map((n) =>
      n.children ? { ...n, children: filtrarNav(n.children, user) } : n,
    )
    .filter((n) => !n.children || n.children.length > 0);
}

/** ¿La ruta actual cae bajo algún `href` de este nodo o sus descendientes? */
function nodeContainsPath(node: NavNode, pathname: string): boolean {
  if (node.href) {
    const isActive =
      node.href === "/inicio" ? pathname === "/inicio" : pathname.startsWith(node.href);
    if (isActive) return true;
  }
  return (node.children ?? []).some((c) => nodeContainsPath(c, pathname));
}

/** Enlace hoja del árbol de navegación. */
function NavLeaf({
  node,
  pathname,
  depth,
  onNavigate,
}: {
  node: NavNode;
  pathname: string;
  depth: number;
  onNavigate?: () => void;
}) {
  const active =
    node.href === "/inicio"
      ? pathname === "/inicio"
      : !!node.href && pathname.startsWith(node.href);
  const Icon = node.icon;
  return (
    <Link
      href={node.href!}
      onClick={onNavigate}
      className={cn(
        "flex min-h-9 items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
        active
          ? "bg-primary text-primary-foreground"
          : "text-navy-foreground/70 hover:bg-white/10 hover:text-navy-foreground",
      )}
      style={depth > 0 ? { paddingLeft: `${depth * 0.75 + 0.75}rem` } : undefined}
    >
      <Icon className="size-4 shrink-0" />
      <span className="truncate">{node.label}</span>
    </Link>
  );
}

/** Grupo colapsable del árbol de navegación (acordeón). */
function NavGroup({
  node,
  pathname,
  depth,
  onNavigate,
}: {
  node: NavNode;
  pathname: string;
  depth: number;
  onNavigate?: () => void;
}) {
  const containsActive = nodeContainsPath(node, pathname);
  const Icon = node.icon;
  const [open, setOpen] = useState(containsActive);

  // Al navegar a una ruta dentro del grupo, abrirlo (sin forzar el cierre manual del usuario).
  useEffect(() => {
    if (containsActive) setOpen(true);
  }, [containsActive]);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger
        className={cn(
          "group flex min-h-9 w-full items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
          containsActive
            ? "font-medium text-navy-foreground"
            : "text-navy-foreground/70 hover:bg-white/10 hover:text-navy-foreground",
        )}
        style={depth > 0 ? { paddingLeft: `${depth * 0.75 + 0.75}rem` } : undefined}
      >
        <Icon className="size-4 shrink-0" />
        <span className="truncate">{node.label}</span>
        <ChevronRight className="ml-auto size-4 shrink-0 transition-transform duration-200 group-data-[panel-open]:rotate-90" />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="grid gap-1 pt-1">
          {node.children!.map((child) => (
            <NavNodeRenderer
              key={child.href ?? child.label}
              node={child}
              pathname={pathname}
              depth={depth + 1}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

function NavNodeRenderer(props: {
  node: NavNode;
  pathname: string;
  depth: number;
  onNavigate?: () => void;
}) {
  return props.node.children ? <NavGroup {...props} /> : <NavLeaf {...props} />;
}

/** Árbol de navegación, reutilizado por la barra lateral (desktop) y el drawer (móvil). */
function NavLinks({
  items,
  pathname,
  onNavigate,
}: {
  items: NavNode[];
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <nav className="grid gap-1">
      {items.map((node) => (
        <NavNodeRenderer
          key={node.href ?? node.label}
          node={node}
          pathname={pathname}
          depth={0}
          onNavigate={onNavigate}
        />
      ))}
    </nav>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const pathname = usePathname();
  const logout = useLogout();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  // Glassmorphism sutil: al hacer scroll, el navbar navy pasa a translúcido + blur.
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const items = filtrarNav(NAV_ITEMS, user);

  return (
    <div className="flex min-h-dvh flex-col">
      {/* Navbar navy full width, siempre visible (sticky) sobre toda la app */}
      <header
        className={cn(
          "sticky top-0 z-40 flex h-14 items-center gap-2 border-b border-white/10 bg-navy px-4 text-navy-foreground transition-colors",
          scrolled &&
            "bg-navy/85 backdrop-blur-sm supports-[backdrop-filter]:bg-navy/75",
        )}
      >
        {/* Hamburguesa + drawer solo en móvil */}
        <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
          <SheetTrigger
            render={
              <Button
                variant="ghost"
                size="icon-sm"
                className="text-navy-foreground hover:bg-white/10 hover:text-navy-foreground md:hidden"
                aria-label="Abrir navegación"
              />
            }
          >
            <MenuIcon />
          </SheetTrigger>
          <SheetContent side="left" className="bg-navy text-navy-foreground">
            <SheetHeader>
              <Image
                src="/logo-minsa.png"
                alt="Ministerio de Salud del Perú"
                width={2000}
                height={408}
                className="h-8 w-auto"
              />
              <SheetTitle className="text-navy-foreground">RENADS</SheetTitle>
            </SheetHeader>
            <div className="overflow-y-auto px-1 pb-4">
              <NavLinks
                items={items}
                pathname={pathname}
                onNavigate={() => setMobileNavOpen(false)}
              />
            </div>
          </SheetContent>
        </Sheet>

        {/* Logo MINSA, arriba a la izquierda, a la altura del título */}
        <Image
          src="/logo-minsa.png"
          alt="Ministerio de Salud del Perú"
          width={2000}
          height={408}
          priority
          className="h-8 w-auto"
        />

        {/* Título del proyecto, centrado. Completo en web; en móvil solo "RENADS". */}
        <span
          title="Registro Nacional de Articulación Docencia-Servicio en Salud - RENADS"
          className="absolute left-1/2 max-w-[55%] -translate-x-1/2 truncate text-center font-bold text-navy-foreground"
        >
          <span className="text-base lg:hidden">RENADS</span>
          <span className="hidden text-lg lg:inline">
            Registro Nacional de Articulación Docencia-Servicio en Salud - RENADS
          </span>
        </span>
        <div className="ml-auto flex items-center gap-1">
          <ThemeToggle />
          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <Button
                  variant="ghost"
                  className="gap-2 px-2 text-navy-foreground hover:bg-white/10 hover:text-navy-foreground"
                />
              }
            >
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
        {/* Barra lateral navy siempre visible (sticky bajo el navbar) en desktop */}
        <aside className="sticky top-14 hidden h-[calc(100dvh-3.5rem)] w-60 shrink-0 self-start overflow-y-auto border-r border-white/10 bg-navy p-4 text-navy-foreground md:block">
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
