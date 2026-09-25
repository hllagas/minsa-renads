import { CheckCircle2, XCircle } from "lucide-react";
import type { ReactNode } from "react";

/**
 * Indicador booleano de tabla: icono ✓ (verde) / ✗ (atenuado) en vez de texto «Sí/No».
 * Cumple `color-not-only` (la forma ✓/✗ distingue el estado sin depender del color) y expone
 * `aria-label` para lectores de pantalla. Devuelve `ReactNode` → usable desde configs `.ts` en el
 * `render` de una columna (`render: (r) => boolIcon(r.activo)`), sin necesidad de JSX en el config.
 */
export function boolIcon(
  value: boolean,
  trueLabel = "Sí",
  falseLabel = "No",
): ReactNode {
  return value ? (
    <CheckCircle2
      className="h-[18px] w-[18px] text-emerald-600"
      role="img"
      aria-label={trueLabel}
    />
  ) : (
    <XCircle
      className="h-[18px] w-[18px] text-muted-foreground"
      role="img"
      aria-label={falseLabel}
    />
  );
}
