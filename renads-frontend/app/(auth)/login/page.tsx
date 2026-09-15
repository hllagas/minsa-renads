"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { ArrowLeftIcon, EyeIcon, EyeOffIcon } from "lucide-react";
import { useMutation } from "@tanstack/react-query";

import { useLogin } from "@/lib/auth/hooks";
import { useAuthStore } from "@/lib/auth/store";
import {
  requestPasswordReset,
  confirmPasswordReset,
} from "@/lib/api/auth";
import { extractApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

// ─── Schemas ──────────────────────────────────────────────────────────────────

const loginSchema = z.object({
  username: z.string().min(1, "El usuario es obligatorio."),
  password: z.string().min(1, "La contraseña es obligatoria."),
});

const forgotRequestSchema = z.object({
  username: z.string().min(1, "El usuario es obligatorio."),
});

const forgotConfirmSchema = z
  .object({
    otp_code: z
      .string()
      .length(6, "El código debe tener exactamente 6 dígitos.")
      .regex(/^\d+$/, "Solo se permiten números."),
    password_nueva: z.string().min(8, "Mínimo 8 caracteres."),
    password_confirm: z.string(),
  })
  .refine((d) => d.password_nueva === d.password_confirm, {
    message: "Las contraseñas no coinciden.",
    path: ["password_confirm"],
  });

type LoginValues = z.infer<typeof loginSchema>;
type ForgotRequestValues = z.infer<typeof forgotRequestSchema>;
type ForgotConfirmValues = z.infer<typeof forgotConfirmSchema>;
type View = "login" | "forgot-request" | "forgot-confirm";

// ─── Componente ───────────────────────────────────────────────────────────────

export default function LoginPage() {
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const { mutate: login, isPending: loginPending } = useLogin();

  const [view, setView] = useState<View>("login");
  const [resetUsername, setResetUsername] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  useEffect(() => {
    if (accessToken) router.replace("/inicio");
  }, [accessToken, router]);

  // ── Formularios ─────────────────────────────────────────────────────────────
  const loginForm = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  const forgotRequestForm = useForm<ForgotRequestValues>({
    resolver: zodResolver(forgotRequestSchema),
    defaultValues: { username: "" },
  });

  const forgotConfirmForm = useForm<ForgotConfirmValues>({
    resolver: zodResolver(forgotConfirmSchema),
    defaultValues: { otp_code: "", password_nueva: "", password_confirm: "" },
  });

  // ── Mutaciones ──────────────────────────────────────────────────────────────
  const requestResetM = useMutation({
    mutationFn: requestPasswordReset,
    onSuccess: () => {
      setResetUsername(forgotRequestForm.getValues("username"));
      setView("forgot-confirm");
    },
    onError: (err: unknown) =>
      toast.error(extractApiError(err) || "Error al solicitar el código. Intenta nuevamente."),
  });

  const confirmResetM = useMutation({
    mutationFn: confirmPasswordReset,
    onSuccess: () => {
      toast.success("Contraseña restablecida. Ya puedes iniciar sesión.");
      forgotConfirmForm.reset();
      setView("login");
    },
    onError: (err: unknown) =>
      toast.error(extractApiError(err) || "Código incorrecto o expirado. Intenta nuevamente."),
  });

  // ── Handlers ────────────────────────────────────────────────────────────────
  function onLogin(values: LoginValues) {
    login(values, {
      onError: () => toast.error("Credenciales inválidas. Verifica usuario y contraseña."),
    });
  }

  function onForgotRequest(values: ForgotRequestValues) {
    requestResetM.mutate(values);
  }

  function onForgotConfirm(values: ForgotConfirmValues) {
    confirmResetM.mutate({
      username: resetUsername,
      otp_code: values.otp_code,
      password_nueva: values.password_nueva,
    });
  }

  function goBack() {
    if (view === "forgot-confirm") {
      setView("forgot-request");
    } else {
      setView("login");
    }
  }

  // ── Textos por vista ────────────────────────────────────────────────────────
  const headingByView: Record<View, string> = {
    login: "Bienvenido",
    "forgot-request": "Recuperar contraseña",
    "forgot-confirm": "Código de verificación",
  };

  const subtitleByView: Record<View, string> = {
    login: "Registro Nacional de Articulación Docencia-Servicio en Salud — RENADS",
    "forgot-request":
      "Ingresa tu nombre de usuario y enviaremos un código de verificación al correo registrado.",
    "forgot-confirm": `Ingresa el código enviado al correo de «${resetUsername}» y elige tu nueva contraseña.`,
  };

  return (
    <div className="flex min-h-dvh">
      {/* ── Panel izquierdo ── */}
      <div className="flex w-full flex-col items-center justify-center bg-white px-8 py-12 sm:px-12 lg:w-[44%] lg:px-16 xl:px-24">
        <div className="w-full max-w-sm">
          {/* Logo */}
          <div className="mb-8 flex justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/logo-minsa.png"
              alt="Logo MINSA"
              className="h-auto w-full max-w-[240px] object-contain"
            />
          </div>

          {/* Botón volver (flujos de recuperación) */}
          {view !== "login" && (
            <button
              type="button"
              className="mb-4 flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
              onClick={goBack}
            >
              <ArrowLeftIcon className="h-4 w-4" />
              Volver
            </button>
          )}

          {/* Encabezado */}
          <div className="mb-6">
            <h1 className="text-center text-lg font-semibold text-gray-900">
              {headingByView[view]}
            </h1>
            <p className="mt-0.5 text-xs text-muted-foreground">{subtitleByView[view]}</p>
          </div>

          {/* ─── Vista: login ─── */}
          {view === "login" && (
            <Form {...loginForm}>
              <form onSubmit={loginForm.handleSubmit(onLogin)} className="space-y-4">
                <FormField
                  control={loginForm.control}
                  name="username"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-gray-700">Usuario</FormLabel>
                      <FormControl>
                        <Input
                          autoComplete="username"
                          autoFocus
                          placeholder="Ingresa tu usuario"
                          className="h-10"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={loginForm.control}
                  name="password"
                  render={({ field }) => (
                    <FormItem>
                      <div className="flex items-center justify-between">
                        <FormLabel className="text-gray-700">Contraseña</FormLabel>
                        <button
                          type="button"
                          className="text-xs text-primary hover:underline"
                          onClick={() => setView("forgot-request")}
                        >
                          ¿Olvidaste tu contraseña?
                        </button>
                      </div>
                      <FormControl>
                        <div className="relative">
                          <Input
                            type={showPassword ? "text" : "password"}
                            autoComplete="current-password"
                            placeholder="Ingresa tu contraseña"
                            className="h-10 pr-10"
                            {...field}
                          />
                          <button
                            type="button"
                            aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                            aria-pressed={showPassword}
                            className="absolute top-1/2 right-2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            onClick={() => setShowPassword((v) => !v)}
                          >
                            {showPassword ? (
                              <EyeOffIcon className="h-4 w-4" />
                            ) : (
                              <EyeIcon className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button
                  type="submit"
                  className="mt-2 h-10 w-full text-sm font-medium"
                  disabled={loginPending}
                >
                  {loginPending ? "Ingresando…" : "Ingresar"}
                </Button>
              </form>
            </Form>
          )}

          {/* ─── Vista: solicitar código ─── */}
          {view === "forgot-request" && (
            <Form {...forgotRequestForm}>
              <form onSubmit={forgotRequestForm.handleSubmit(onForgotRequest)} className="space-y-4">
                <FormField
                  control={forgotRequestForm.control}
                  name="username"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-gray-700">Usuario</FormLabel>
                      <FormControl>
                        <Input
                          autoComplete="username"
                          autoFocus
                          placeholder="Ingresa tu usuario"
                          className="h-10"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button
                  type="submit"
                  className="mt-2 h-10 w-full text-sm font-medium"
                  disabled={requestResetM.isPending}
                >
                  {requestResetM.isPending ? "Enviando…" : "Enviar código"}
                </Button>
              </form>
            </Form>
          )}

          {/* ─── Vista: confirmar OTP + nueva contraseña ─── */}
          {view === "forgot-confirm" && (
            <Form {...forgotConfirmForm}>
              <form onSubmit={forgotConfirmForm.handleSubmit(onForgotConfirm)} className="space-y-4">
                <FormField
                  control={forgotConfirmForm.control}
                  name="otp_code"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-gray-700">Código de verificación</FormLabel>
                      <FormControl>
                        <Input
                          inputMode="numeric"
                          autoComplete="one-time-code"
                          autoFocus
                          maxLength={6}
                          placeholder="123456"
                          className="h-10 text-center text-xl tracking-widest"
                          {...field}
                          onChange={(e) =>
                            field.onChange(e.target.value.replace(/\D/g, ""))
                          }
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={forgotConfirmForm.control}
                  name="password_nueva"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-gray-700">Nueva contraseña</FormLabel>
                      <FormControl>
                        <div className="relative">
                          <Input
                            type={showNewPassword ? "text" : "password"}
                            autoComplete="new-password"
                            placeholder="Mínimo 8 caracteres"
                            className="h-10 pr-10"
                            {...field}
                          />
                          <button
                            type="button"
                            aria-label={showNewPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                            className="absolute top-1/2 right-2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                            onClick={() => setShowNewPassword((v) => !v)}
                          >
                            {showNewPassword ? (
                              <EyeOffIcon className="h-4 w-4" />
                            ) : (
                              <EyeIcon className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={forgotConfirmForm.control}
                  name="password_confirm"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-gray-700">Confirmar contraseña</FormLabel>
                      <FormControl>
                        <Input
                          type={showNewPassword ? "text" : "password"}
                          autoComplete="new-password"
                          placeholder="Repite la nueva contraseña"
                          className="h-10"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button
                  type="submit"
                  className="mt-2 h-10 w-full text-sm font-medium"
                  disabled={confirmResetM.isPending}
                >
                  {confirmResetM.isPending ? "Restableciendo…" : "Restablecer contraseña"}
                </Button>
              </form>
            </Form>
          )}

          <p className="mt-8 text-center text-xs text-muted-foreground">© MINSA PERÚ</p>
        </div>
      </div>

      {/* ── Panel derecho: imagen institucional ── */}
      <div className="relative hidden lg:block lg:flex-1">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: "url('/portada_login.jpg')" }}
        />
        <div className="absolute inset-0 bg-gradient-to-br from-slate-950/60 via-slate-900/35 to-slate-950/65" />
      </div>
    </div>
  );
}
