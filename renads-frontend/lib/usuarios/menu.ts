/**
 * Secciones del índice `/usuarios`. La visibilidad de cada tarjeta depende del acceso:
 * `superuser` exige superusuario puro; `admin` admite superusuario o `Administrador RENADS`.
 */
export type UsuariosAccess = "superuser" | "admin";

export interface UsuariosMenuItem {
  href: string;
  title: string;
  description: string;
  access: UsuariosAccess;
}

export const USUARIOS_MENU: UsuariosMenuItem[] = [
  {
    href: "/usuarios/cuentas",
    title: "Cuentas",
    description: "Crear, editar, desactivar usuarios y cambiar contraseñas.",
    access: "superuser",
  },
  {
    href: "/usuarios/roles",
    title: "Roles",
    description: "Definir roles y los permisos que agrupan.",
    access: "superuser",
  },
  {
    href: "/usuarios/permisos",
    title: "Permisos",
    description: "Consultar el catálogo de permisos (solo lectura).",
    access: "superuser",
  },
  {
    href: "/usuarios/perfiles",
    title: "Perfiles institucionales",
    description: "Vínculos usuario ↔ entidad para el alcance.",
    access: "admin",
  },
];
