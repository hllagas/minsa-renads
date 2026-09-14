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

/** Estilo translúcido compartido para los inputs sobre el cristal (legibles sobre la imagen). */
const GLASS_INPUT =
  "border-white/25 bg-white/10 text-white placeholder:text-white/50 focus-visible:ring-white/40";

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
      onError: () => toast.error("Credenciales inválidas. Verifica usuario y contraseña."),
    });
  }

  return (
    <div className="relative flex min-h-dvh items-center justify-center overflow-hidden p-4 sm:p-6 lg:justify-start lg:pl-16 xl:pl-24">
      {/* Imagen de fondo institucional (RENADS 2.0). */}
      <div
        aria-hidden
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: "url('/portada_login.png')" }}
      />
      {/* Velo suave para dar contraste al formulario sin ocultar la imagen. */}
      <div
        aria-hidden
        className="absolute inset-0 bg-gradient-to-br from-slate-950/60 via-slate-900/35 to-slate-950/60"
      />

      {/* Tarjeta «flotante» de cristal: fondo translúcido + desenfoque + sombra amplia. */}
      <Card className="relative z-10 w-full max-w-md rounded-2xl border border-white/15 bg-white/10 text-white shadow-2xl ring-1 ring-white/10 backdrop-blur-xl backdrop-saturate-150">
        <CardHeader className="items-center text-center">
          <CardTitle className="text-2xl tracking-wide text-white">Bienvenido</CardTitle>
          <CardDescription className="text-white/75">
            Registro Nacional de Articulación Docencia–Servicio en Salud
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4">
              <FormField
                control={form.control}
                name="username"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-white/90">Usuario</FormLabel>
                    <FormControl>
                      <Input
                        autoComplete="username"
                        autoFocus
                        className={GLASS_INPUT}
                        {...field}
                      />
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
                    <FormLabel className="text-white/90">Contraseña</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type={showPassword ? "text" : "password"}
                          autoComplete="current-password"
                          className={`pr-10 ${GLASS_INPUT}`}
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
                          className="absolute top-1/2 right-1 -translate-y-1/2 text-white/70 hover:bg-white/10 hover:text-white"
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
              <Button type="submit" className="mt-1 w-full" disabled={isPending}>
                {isPending ? "Ingresando…" : "Ingresar"}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
