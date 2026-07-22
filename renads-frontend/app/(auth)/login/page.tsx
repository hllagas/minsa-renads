"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { EyeIcon, EyeOffIcon } from "lucide-react";

import { useLogin } from "@/lib/auth/hooks";
import { useAuthStore } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

const loginSchema = z.object({
  username: z.string().min(1, "El usuario es obligatorio."),
  password: z.string().min(1, "La contraseña es obligatoria."),
});

type LoginValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const { mutate, isPending } = useLogin();
  const [showPassword, setShowPassword] = useState(false);

  // Si ya hay sesión, no mostrar el login.
  useEffect(() => {
    if (accessToken) router.replace("/inicio");
  }, [accessToken, router]);

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  function onSubmit(values: LoginValues) {
    mutate(values, {
      onSuccess: () => router.replace("/inicio"),
      onError: () =>
        toast.error("Credenciales inválidas. Verifica usuario y contraseña."),
    });
  }

  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      {/* Panel izquierdo minimalista relacionado al proyecto (docencia–servicio en salud).
          Oculto en móvil; ilustración vectorial propia (sin assets externos) sobre gradiente. */}
      <BrandPanel />

      <div className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-background p-0 sm:p-6">
        {/* Capa de gradiente moderno (decorativa). Usa tokens --chart-* para coherencia claro/oscuro. */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_55%_at_80%_15%,color-mix(in_oklch,var(--color-chart-1),transparent_82%),transparent_70%),radial-gradient(55%_55%_at_12%_92%,color-mix(in_oklch,var(--color-chart-5),transparent_85%),transparent_70%)] lg:hidden"
        />

        <Card className="relative z-10 flex min-h-dvh w-full max-w-sm flex-col justify-center rounded-none border-0 bg-transparent shadow-none sm:min-h-0 sm:block sm:rounded-xl sm:border sm:bg-card sm:shadow-xl lg:border-0 lg:bg-transparent lg:shadow-none">
        <CardHeader>
          <CardTitle className="text-xl">RENADS</CardTitle>
          <CardDescription>Inicia sesión para continuar.</CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4">
              <FormField
                control={form.control}
                name="username"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Usuario</FormLabel>
                    <FormControl>
                      <Input autoComplete="username" autoFocus {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Contraseña</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type={showPassword ? "text" : "password"}
                          autoComplete="current-password"
                          className="pr-10"
                          {...field}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-sm"
                          aria-label={
                            showPassword
                              ? "Ocultar contraseña"
                              : "Mostrar contraseña"
                          }
                          aria-pressed={showPassword}
                          className="absolute top-1/2 right-1 -translate-y-1/2 text-muted-foreground"
                          onClick={() => setShowPassword((v) => !v)}
                        >
                          {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                        </Button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" className="w-full" disabled={isPending}>
                {isPending ? "Ingresando…" : "Ingresar"}
              </Button>
            </form>
          </Form>
        </CardContent>
        </Card>
      </div>
    </div>
  );
}

/**
 * Panel de marca lateral (izquierda) — minimalista, tema docencia–servicio en salud.
 * Ilustración vectorial propia: latido/ECG (servicio en salud) que se convierte en birrete
 * (docencia). Solo visible en ≥ lg; en pantallas menores el login queda a una columna.
 */
function BrandPanel() {
  return (
    <aside className="relative hidden overflow-hidden bg-[linear-gradient(150deg,#3b0d6b_0%,#5b21b6_42%,#2e1065_100%)] text-violet-50 lg:flex lg:flex-col lg:justify-between lg:p-12">
      {/* Halos suaves violeta/fucsia sobre el gradiente base (estética IA minimalista). */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_55%_at_18%_12%,rgba(216,180,254,0.30),transparent_70%),radial-gradient(55%_55%_at_88%_88%,rgba(244,114,182,0.22),transparent_70%)]"
      />

      <div className="relative z-10 flex items-center gap-3">
        <span className="text-lg font-semibold tracking-[0.2em]">RENADS</span>
      </div>

      <div className="relative z-10 flex flex-1 items-center justify-center py-10">
        <BrandMark />
      </div>

      <div className="relative z-10 max-w-md">
        <h2 className="text-2xl leading-tight font-semibold">
          Articulación Docencia–Servicio en Salud
        </h2>
        <p className="mt-3 text-sm text-violet-100/80">
          Registro Nacional que integra la formación de internos con la atención en los
          establecimientos de salud del país.
        </p>
        <p className="mt-6 text-xs tracking-widest text-violet-200/60 uppercase">
          MINSA · Perú
        </p>
      </div>
    </aside>
  );
}

/**
 * Ilustración minimalista: perfil humano de línea (evoca la referencia IA) con un halo suave
 * y partículas «neuronales». Trazo único, monocromo violeta claro; sin detalles realistas.
 */
function BrandMark() {
  return (
    <svg
      width="260"
      height="260"
      viewBox="0 0 260 260"
      fill="none"
      aria-hidden
      className="text-violet-100"
    >
      {/* Halos concéntricos. */}
      <circle cx="130" cy="130" r="104" stroke="currentColor" strokeOpacity="0.18" strokeWidth="1.5" />
      <circle cx="130" cy="130" r="78" stroke="currentColor" strokeOpacity="0.12" strokeWidth="1.5" />

      {/* Silueta de perfil (rostro hacia la izquierda). */}
      <path
        d="M168 54
           C126 40 84 58 78 104
           C76 116 68 120 72 130
           C80 134 80 138 68 146
           C62 150 66 158 76 160
           C70 166 74 178 92 182
           C98 196 108 204 122 204
           C150 204 172 150 176 104
           C178 82 186 62 168 54 Z"
        fill="currentColor"
        fillOpacity="0.08"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinejoin="round"
        strokeLinecap="round"
      />

      {/* Partículas «neuronales» (idea / formación). */}
      <g fill="currentColor">
        <circle cx="120" cy="86" r="3" />
        <circle cx="140" cy="74" r="2.2" fillOpacity="0.8" />
        <circle cx="150" cy="100" r="2.6" />
        <circle cx="132" cy="108" r="1.8" fillOpacity="0.7" />
        <circle cx="158" cy="128" r="2" fillOpacity="0.6" />
      </g>
      <g stroke="currentColor" strokeWidth="1.2" strokeOpacity="0.45">
        <path d="M120 86 L140 74" />
        <path d="M120 86 L132 108" />
        <path d="M140 74 L150 100" />
        <path d="M150 100 L158 128" />
        <path d="M132 108 L150 100" />
      </g>
    </svg>
  );
}
