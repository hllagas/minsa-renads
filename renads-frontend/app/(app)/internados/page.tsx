"use client";

import Link from "next/link";
import { GraduationCap, Users, ClipboardList } from "lucide-react";

import { PageHeader } from "@/components/data/page-header";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface SectionCard {
  href: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}

/** Índice del módulo Internados: tarjetas de Estudiantes, Tutores e Internos. */
const CARDS: SectionCard[] = [
  {
    href: "/internados/personas/students",
    title: "Estudiantes",
    description: "Estudiantes en proceso de internado.",
    icon: <GraduationCap className="size-6 text-primary" />,
  },
  {
    href: "/internados/personas/tutors",
    title: "Tutores",
    description: "Docentes/tutores responsables.",
    icon: <Users className="size-6 text-primary" />,
  },
  {
    href: "/internados/internos",
    title: "Internos",
    description: "Internados, rotaciones y autorizaciones.",
    icon: <ClipboardList className="size-6 text-primary" />,
  },
];

export default function InternadosIndexPage() {
  return (
    <div className="grid gap-6">
      <PageHeader
        title="Internados"
        description="Gestión de estudiantes, tutores e internos."
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CARDS.map((c) => (
          <Link key={c.href} href={c.href}>
            <Card className="h-full transition-colors hover:bg-muted/50">
              <CardHeader>
                <div className="mb-2 flex size-11 items-center justify-center rounded-lg bg-primary/10">
                  {c.icon}
                </div>
                <CardTitle>{c.title}</CardTitle>
                <CardDescription>{c.description}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
