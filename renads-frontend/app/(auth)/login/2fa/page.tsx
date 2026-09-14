"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { ShieldCheckIcon } from "lucide-react";

import { useVerify2fa } from "@/lib/auth/hooks";
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

const otpSchema = z.object({
  otp_code: z
    .string()
    .min(6, "El código debe tener 6 dígitos.")
    .max(8, "El código no puede tener más de 8 dígitos.")
    .regex(/^\d+$/, "El código solo puede contener números."),
});

type OtpValues = z.infer<typeof otpSchema>;

const GLASS_INPUT =
  "border-white/25 bg-white/10 text-white placeholder:text-white/50 focus-visible:ring-white/40";

export default function TwoFactorPage() {
  const router = useRouter();
  const pendingTwoFactor = useAuthStore((s) => s.pendingTwoFactor);
  const { mutate, isPending } = useVerify2fa();

  // Si no hay flujo 2FA activo, volver al login.
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
    <div className="relative flex min-h-dvh items-center justify-center overflow-hidden p-4 sm:p-6 lg:justify-start lg:pl-16 xl:pl-24">
      <div
        aria-hidden
        className="absolute inset-0 bg-cover bg-center"
        style={{ backgroundImage: "url('/portada_login.png')" }}
      />
      <div
        aria-hidden
        className="absolute inset-0 bg-gradient-to-br from-slate-950/60 via-slate-900/35 to-slate-950/60"
      />

      <Card className="relative z-10 w-full max-w-md rounded-2xl border border-white/15 bg-white/10 text-white shadow-2xl ring-1 ring-white/10 backdrop-blur-xl backdrop-saturate-150">
        <CardHeader className="items-center text-center">
          <ShieldCheckIcon className="mb-2 h-10 w-10 text-white/80" />
          <CardTitle className="text-2xl tracking-wide text-white">
            Verificación de identidad
          </CardTitle>
          <CardDescription className="text-white/75">
            {isTotp
              ? "Ingresa el código de 6 dígitos de tu aplicación autenticadora."
              : "Ingresa el código de 6 dígitos enviado a tu correo electrónico."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4">
              <FormField
                control={form.control}
                name="otp_code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-white/90">Código de verificación</FormLabel>
                    <FormControl>
                      <Input
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        autoFocus
                        maxLength={8}
                        placeholder="000000"
                        className={`text-center text-xl tracking-widest ${GLASS_INPUT}`}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" className="mt-1 w-full" disabled={isPending}>
                {isPending ? "Verificando…" : "Verificar"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="w-full text-white/60 hover:bg-white/10 hover:text-white"
                onClick={() => router.replace("/login")}
              >
                Volver al inicio de sesión
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
