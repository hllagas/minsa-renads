"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { ArrowLeftIcon } from "lucide-react";

import { useVerify2fa } from "@/lib/auth/hooks";
import { useAuthStore } from "@/lib/auth/store";
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

const otpSchema = z.object({
  otp_code: z
    .string()
    .min(6, "El código debe tener 6 dígitos.")
    .max(8, "El código no puede tener más de 8 dígitos.")
    .regex(/^\d+$/, "El código solo puede contener números."),
});

type OtpValues = z.infer<typeof otpSchema>;

export default function TwoFactorPage() {
  const router = useRouter();
  const pendingTwoFactor = useAuthStore((s) => s.pendingTwoFactor);
  const { mutate, isPending } = useVerify2fa();

  useEffect(() => {
    if (!pendingTwoFactor) router.replace("/login");
  }, [pendingTwoFactor, router]);

  const form = useForm<OtpValues>({
    resolver: zodResolver(otpSchema),
    defaultValues: { otp_code: "" },
  });

  function onSubmit(values: OtpValues) {
    if (!pendingTwoFactor) return;
    mutate(
      { session_token: pendingTwoFactor.sessionToken, otp_code: values.otp_code },
      {
        onSuccess: () => router.replace("/inicio"),
        onError: () => {
          toast.error("Código incorrecto o expirado. Intenta nuevamente.");
          form.reset();
        },
      },
    );
  }

  const isTotp = pendingTwoFactor?.method === "TOTP";

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

          {/* Botón volver */}
          <button
            type="button"
            className="mb-4 flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
            onClick={() => router.replace("/login")}
          >
            <ArrowLeftIcon className="h-4 w-4" />
            Volver al inicio de sesión
          </button>

          {/* Encabezado */}
          <div className="mb-6">
            <h1 className="text-lg font-semibold text-gray-900">Verificación de identidad</h1>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {isTotp
                ? "Ingresa el código de 6 dígitos de tu aplicación autenticadora."
                : "Ingresa el código de 6 dígitos enviado a tu correo electrónico."}
            </p>
          </div>

          {/* Formulario OTP */}
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="otp_code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-700">Código de verificación</FormLabel>
                    <FormControl>
                      <Input
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        autoFocus
                        maxLength={8}
                        placeholder="000000"
                        className="h-10 text-center text-xl tracking-widest"
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
                disabled={isPending}
              >
                {isPending ? "Verificando…" : "Verificar"}
              </Button>
            </form>
          </Form>

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
