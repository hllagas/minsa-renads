import { Badge } from "@/components/ui/badge";

interface TwoFactorStatusProps {
  enabled: boolean | undefined;
  method: "TOTP" | "EMAIL" | "" | undefined;
}

/**
 * Widget de solo lectura que muestra el estado actual del 2FA del usuario.
 * Recibe los valores desde el componente padre (leídos de `AuthUser`).
 */
export function TwoFactorStatus({ enabled, method }: TwoFactorStatusProps) {
  if (!enabled) {
    return (
      <Badge
        variant="outline"
        aria-label="Segundo factor de autenticación: no activado"
      >
        No activado
      </Badge>
    );
  }

  if (method === "TOTP") {
    return (
      <Badge
        className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 border-green-300"
        aria-label="Segundo factor de autenticación activo: app autenticadora"
      >
        Activo · App autenticadora
      </Badge>
    );
  }

  if (method === "EMAIL") {
    return (
      <Badge
        className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 border-green-300"
        aria-label="Segundo factor de autenticación activo: correo electrónico"
      >
        Activo · Correo electrónico
      </Badge>
    );
  }

  // Activo pero sin método conocido — caso de borde
  return (
    <Badge
      className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 border-green-300"
      aria-label="Segundo factor de autenticación activo"
    >
      Activo
    </Badge>
  );
}
