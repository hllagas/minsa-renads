"use client";

import Link from "next/link";

import { CATALOGO_ENTITY_MENU } from "@/lib/catalogos/entities";
import { CATALOG_MENU } from "@/lib/catalogos/catalogs";
import { useAuthStore, userHasRole } from "@/lib/auth/store";
import { PageHeader } from "@/components/data/page-header";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface CardLink {
  href: string;
  title: string;
  description: string;
}

/** Tarjeta enlazada reutilizable del índice. */
function LinkCard({ href, title, description }: CardLink) {
  return (
    <Link href={href}>
      <Card className="h-full transition-colors hover:bg-muted/50">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
      </Card>
    </Link>
  );
}

/** Sección del índice: título + grilla de tarjetas. */
function Section({ title, cards }: { title: string; cards: CardLink[] }) {
  return (
    <section className="grid gap-3">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((c) => (
          <LinkCard key={c.href} {...c} />
        ))}
      </div>
    </section>
  );
}

/** Índice de Catálogos — mantenimiento de tablas maestras (Módulo 6). */
export default function CatalogosPage() {
  const user = useAuthStore((s) => s.user);
  const canAudit = userHasRole(user, "Administrador RENADS", "Auditor");

  const entidadCards: CardLink[] = CATALOGO_ENTITY_MENU.map((e) => ({
    href: `/catalogos/entidades/${e.slug}`,
    title: e.title,
    description: `Gestionar ${e.title.toLowerCase()}.`,
  }));

  const catalogoCards: CardLink[] = CATALOG_MENU.map((c) => ({
    href: `/catalogos/listas/${c.slug}`,
    title: c.title,
    description: "Consulta (solo lectura).",
  }));

  return (
    <div className="grid gap-8">
      <PageHeader
        title="Catálogos"
        description="Mantenimiento de tablas maestras del sistema."
      />

      <Section title="Entidades" cards={entidadCards} />

      <Section
        title="Representantes"
        cards={[
          {
            href: "/catalogos/representantes",
            title: "Representantes",
            description: "Representantes de órganos, unidades, IPRESS y CONAPRES.",
          },
        ]}
      />

      <Section title="Catálogos" cards={catalogoCards} />

      <Section
        title="Documentos"
        cards={[
          {
            href: "/catalogos/documentos",
            title: "Documentos",
            description: "Gestión documental polimórfica con versionado.",
          },
        ]}
      />

      {canAudit ? (
        <Section
          title="Auditoría"
          cards={[
            {
              href: "/catalogos/auditoria",
              title: "Bitácora de auditoría",
              description: "Consulta de la bitácora del sistema.",
            },
          ]}
        />
      ) : null}
    </div>
  );
}
