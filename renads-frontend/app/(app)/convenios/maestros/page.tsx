"use client";

import Link from "next/link";

import { ENTITY_MENU } from "@/lib/convenios/entities";
import { PageHeader } from "@/components/data/page-header";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/** Índice de entidades maestras del módulo Convenios. */
export default function MaestrosPage() {
  return (
    <div>
      <PageHeader
        title="Maestros"
        description="Catálogos y entidades base de Convenios."
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {ENTITY_MENU.map((e) => (
          <Link key={e.slug} href={`/convenios/maestros/${e.slug}`}>
            <Card className="transition-colors hover:bg-muted/50">
              <CardHeader>
                <CardTitle>{e.title}</CardTitle>
                <CardDescription>Gestionar {e.title.toLowerCase()}.</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
