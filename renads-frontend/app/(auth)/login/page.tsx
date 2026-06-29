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
    <div className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-background p-0 sm:p-6">
      {/* Capa de gradiente moderno (decorativa). Usa tokens --chart-* para coherencia claro/oscuro. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_55%_at_80%_15%,color-mix(in_oklch,var(--color-chart-1),transparent_82%),transparent_70%),radial-gradient(55%_55%_at_12%_92%,color-mix(in_oklch,var(--color-chart-5),transparent_85%),transparent_70%)]"
      />

      <Card className="relative z-10 flex min-h-dvh w-full max-w-sm flex-col justify-center rounded-none border-0 bg-transparent shadow-none sm:min-h-0 sm:block sm:rounded-xl sm:border sm:bg-card sm:shadow-xl">
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
  );
}
