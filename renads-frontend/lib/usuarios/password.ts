/**
 * Generación de contraseñas seguras para el alta de usuarios (`/usuarios/cuentas`).
 *
 * Código de cliente (`"use client"`): usa Web Crypto (`crypto.getRandomValues`) — nunca
 * `Math.random()`, que no es criptográficamente seguro. La contraseña generada se prellena en el
 * campo `password` del formulario de alta (write-only) para que el administrador la vea/copie antes
 * de guardar; el backend la recibe tal cual en el POST.
 */

/** Conjuntos de caracteres (sin ambiguos `l/1/I`, `O/0` para facilitar la lectura/copia). */
const MINUSCULAS = "abcdefghijkmnpqrstuvwxyz";
const MAYUSCULAS = "ABCDEFGHJKLMNPQRSTUVWXYZ";
const DIGITOS = "23456789";
const SIMBOLOS = "!@#$%&*+-_?";
const TODOS = MINUSCULAS + MAYUSCULAS + DIGITOS + SIMBOLOS;

/** Entero aleatorio criptográficamente seguro en `[0, max)` (sin sesgo de módulo). */
function randomInt(max: number): number {
  const buf = new Uint32Array(1);
  // Rango máximo múltiplo de `max` para descartar valores que introducirían sesgo de módulo.
  const limite = Math.floor(0xffffffff / max) * max;
  let n: number;
  do {
    crypto.getRandomValues(buf);
    n = buf[0];
  } while (n >= limite);
  return n % max;
}

/** Devuelve un carácter aleatorio (seguro) del conjunto dado. */
function pick(pool: string): string {
  return pool[randomInt(pool.length)];
}

/** Mezcla in-place con Fisher–Yates usando aleatoriedad segura. */
function shuffle(chars: string[]): string[] {
  for (let i = chars.length - 1; i > 0; i--) {
    const j = randomInt(i + 1);
    [chars[i], chars[j]] = [chars[j], chars[i]];
  }
  return chars;
}

/**
 * Genera una contraseña segura de `longitud` caracteres (por defecto 12) que garantiza al menos
 * 1 minúscula, 1 mayúscula, 1 dígito y 1 símbolo. Llamadas sucesivas devuelven cadenas distintas.
 * Longitud mínima efectiva: 4 (un carácter por grupo).
 */
export function generarPassword(longitud = 12): string {
  const total = Math.max(4, Math.floor(longitud));
  // Garantiza un carácter de cada grupo obligatorio…
  const chars = [pick(MINUSCULAS), pick(MAYUSCULAS), pick(DIGITOS), pick(SIMBOLOS)];
  // …y completa el resto desde el conjunto total.
  for (let i = chars.length; i < total; i++) chars.push(pick(TODOS));
  return shuffle(chars).join("");
}
