"use client";

import Link from "next/link";

import { PERSON_MENU } from "@/lib/internados/persons";
import { PageHeader } from "@/components/data/page-header";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/** Índice de personas del módulo Internados (internos, tutores). */
export default function PersonasPage() {
  return (
    <div>
      <PageHeader title="Personas" description="Internos y tutores." />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {PERSON_MENU.map((e) => (
          <Link key={e.slug} href={`/internados/personas/${e.slug}`}>
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
