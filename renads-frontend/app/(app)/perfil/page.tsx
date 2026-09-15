"use client";

import { useState } from "react";
import { MailIcon, ShieldCheckIcon, UserIcon } from "lucide-react";

import { useAuthStore } from "@/lib/auth/store";
import { PageHeader } from "@/components/data/page-header";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { TwoFactorStatus } from "@/components/auth/two-factor-status";
import { TwoFactorMethodSelector } from "@/components/auth/two-factor-method-selector";
import { TotpSetupDialog } from "@/components/auth/totp-setup-dialog";
import { EmailSetupDialog } from "@/components/auth/email-setup-dialog";
import { TwoFactorDisableDialog } from "@/components/auth/two-factor-disable-dialog";

/** Iniciales (máx. 2) para el avatar. */
function iniciales(nombre: string): string {
  return nombre
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

/** Vista de perfil: información básica del usuario autenticado (datos de `/auth/me/`). */
export default function PerfilPage() {
  const user = useAuthStore((s) => s.user);

  // Estado de diálogos 2FA
  const [methodSelectorOpen, setMethodSelectorOpen] = useState(false);
  const [totpDialogOpen, setTotpDialogOpen] = useState(false);
  const [emailDialogOpen, setEmailDialogOpen] = useState(false);
  const [disableDialogOpen, setDisableDialogOpen] = useState(false);

  if (!user) {
    return (
      <div>
        <PageHeader title="Perfil" />
        <p className="text-sm text-muted-foreground">
          No hay una sesión activa.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <PageHeader title="Perfil" description="Tu información de cuenta y alcance." />

      {/* Identidad */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <Avatar className="size-14">
              <AvatarFallback className="text-lg">
                {iniciales(user.nombre || user.username)}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <CardTitle className="truncate text-lg">{user.nombre}</CardTitle>
              <CardDescription className="truncate">
                @{user.username}
              </CardDescription>
            </div>
            {user.es_superusuario ? (
              <Badge variant="secondary" className="ml-auto gap-1">
                <ShieldCheckIcon />
                Superusuario
              </Badge>
            ) : null}
          </div>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-4 sm:grid-cols-2">
            <div className="flex items-start gap-3">
              <MailIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0">
                <dt className="text-xs text-muted-foreground">Correo</dt>
                <dd className="truncate text-sm">{user.email || "—"}</dd>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <UserIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0">
                <dt className="text-xs text-muted-foreground">Usuario</dt>
                <dd className="truncate text-sm">{user.username}</dd>
              </div>
            </div>
          </dl>
        </CardContent>
      </Card>

      {/* Roles */}
      <Card>
        <CardHeader>
          <CardTitle>Roles</CardTitle>
          <CardDescription>Grupos asignados a tu cuenta.</CardDescription>
        </CardHeader>
        <CardContent>
          {user.grupos.length ? (
            <div className="flex flex-wrap gap-2">
              {user.grupos.map((g) => (
                <Badge key={g} variant="outline">
                  {g}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Sin roles asignados.</p>
          )}
        </CardContent>
      </Card>

      {/* Perfiles institucionales */}
      <Card>
        <CardHeader>
          <CardTitle>Perfiles institucionales</CardTitle>
          <CardDescription>Entidades dentro de tu ámbito.</CardDescription>
        </CardHeader>
        <CardContent>
          {user.perfiles.length ? (
            <ul className="grid gap-3">
              {user.perfiles.map((p, i) => (
                <li
                  key={`${p.tipo_entidad}-${p.id_objeto}-${i}`}
                  className="flex items-center justify-between gap-3 rounded-md border p-3"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{p.entidad}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {p.tipo_entidad}
                    </p>
                  </div>
                  <Badge variant="secondary" className="shrink-0">
                    {p.rol}
                  </Badge>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              Sin perfiles institucionales.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Seguridad — gestión del segundo factor de autenticación */}
      <Card>
        <CardHeader>
          <CardTitle>Seguridad</CardTitle>
          <CardDescription>Gestión del segundo factor de autenticación.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-col gap-1">
              <p className="text-sm font-medium">Segundo factor (2FA)</p>
              <TwoFactorStatus
                enabled={user.two_factor_enabled}
                method={user.two_factor_method}
              />
            </div>
            <div className="shrink-0">
              {!user.two_factor_enabled ? (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setMethodSelectorOpen(true)}
                >
                  Activar 2FA
                </Button>
              ) : (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setDisableDialogOpen(true)}
                >
                  Desactivar 2FA
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Diálogos 2FA */}
      <TwoFactorMethodSelector
        open={methodSelectorOpen}
        onOpenChange={setMethodSelectorOpen}
        userEmail={user.email}
        onSelectTotp={() => setTotpDialogOpen(true)}
        onSelectEmail={() => setEmailDialogOpen(true)}
      />
      <TotpSetupDialog
        open={totpDialogOpen}
        onOpenChange={setTotpDialogOpen}
      />
      <EmailSetupDialog
        open={emailDialogOpen}
        onOpenChange={setEmailDialogOpen}
        userEmail={user.email}
      />
      {user.two_factor_enabled && user.two_factor_method && (
        <TwoFactorDisableDialog
          open={disableDialogOpen}
          onOpenChange={setDisableDialogOpen}
          method={user.two_factor_method as "TOTP" | "EMAIL"}
        />
      )}
    </div>
  );
}
