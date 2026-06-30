"use client";

import { useRef, type ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  motion,
  useMotionValue,
  useReducedMotion,
  useSpring,
  type Variants,
} from "framer-motion";
import {
  ActivityIcon,
  ArrowRightIcon,
  CheckIcon,
  FileTextIcon,
  ShieldCheckIcon,
  UsersIcon,
} from "lucide-react";

import { ParticlesCanvas } from "@/components/landing/particles-canvas";
import { ThemeToggle } from "@/components/layout/theme-toggle";

/* ───────────────────────── helpers de estilo ───────────────────────── */

/** Tarjeta glass adaptada a fondo claro (glassmorphism sutil). */
const GLASS =
  "rounded-2xl border border-[var(--ld-glass-border)] bg-[var(--ld-glass-bg)] backdrop-blur-xl shadow-[0_8px_30px_rgba(2,6,23,0.06)]";

/* ───────────────────────── animaciones ───────────────────────── */

const wordContainer: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
};
const wordItem: Variants = {
  hidden: { opacity: 0, y: 60, filter: "blur(8px)" },
  show: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] },
  },
};

const revealContainer: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.1 } },
};
const revealItem: Variants = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

/** Encabezado de headline con stagger por palabra. */
function StaggerWords({ text, className }: { text: string; className?: string }) {
  const reduced = useReducedMotion();
  if (reduced) return <h1 className={className}>{text}</h1>;
  return (
    <motion.h1
      className={className}
      variants={wordContainer}
      initial="hidden"
      animate="show"
    >
      {text.split(" ").map((w, i) => (
        <span key={i} className="inline-block overflow-hidden pb-1">
          <motion.span className="inline-block" variants={wordItem}>
            {w}
            {" "}
          </motion.span>
        </span>
      ))}
    </motion.h1>
  );
}

/** Botón magnético: sigue al cursor con resorte. */
function MagneticButton({
  children,
  className,
  href,
}: {
  children: ReactNode;
  className?: string;
  href: string;
}) {
  const reduced = useReducedMotion();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 250, damping: 18 });
  const sy = useSpring(y, { stiffness: 250, damping: 18 });
  const ref = useRef<HTMLAnchorElement>(null);

  function onMove(e: React.MouseEvent) {
    if (reduced || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    x.set((e.clientX - (r.left + r.width / 2)) * 0.3);
    y.set((e.clientY - (r.top + r.height / 2)) * 0.3);
  }
  function reset() {
    x.set(0);
    y.set(0);
  }

  return (
    <motion.a
      ref={ref}
      href={href}
      onMouseMove={onMove}
      onMouseLeave={reset}
      style={{ x: sx, y: sy }}
      className={className}
    >
      {children}
    </motion.a>
  );
}

/** Tarjeta con tilt 3D en hover (máx 5°). */
function TiltCard({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduced = useReducedMotion();
  const rx = useMotionValue(0);
  const ry = useMotionValue(0);
  const srx = useSpring(rx, { stiffness: 200, damping: 15 });
  const sry = useSpring(ry, { stiffness: 200, damping: 15 });
  const ref = useRef<HTMLDivElement>(null);

  function onMove(e: React.MouseEvent) {
    if (reduced || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - 0.5;
    const py = (e.clientY - r.top) / r.height - 0.5;
    ry.set(px * 10);
    rx.set(-py * 10);
  }
  function reset() {
    rx.set(0);
    ry.set(0);
  }

  return (
    <motion.div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={reset}
      style={{ rotateX: srx, rotateY: sry, transformStyle: "preserve-3d" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/** Sección que se revela al entrar en viewport. */
function Reveal({
  children,
  className,
  id,
}: {
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <motion.section
      id={id}
      className={className}
      variants={revealContainer}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-100px" }}
    >
      {children}
    </motion.section>
  );
}

/* ───────────────────────── datos (RENADS) ───────────────────────── */

const NAV_LINKS = [
  { label: "Módulos", href: "#features" },
  { label: "Cómo funciona", href: "#how" },
  { label: "Testimonios", href: "#testimonials" },
];

const ENTIDADES = [
  "MINSA",
  "DIGEP",
  "CONAPRES",
  "OGAJ",
  "Secretaría General",
  "Universidades",
  "IPRESS",
];

const FEATURES = [
  {
    icon: FileTextIcon,
    title: "Gestión de Convenios",
    desc: "Convenios Marco y Específicos: evaluación técnica (DIGEP), opinión CONAPRES y jurídica (OGAJ), firma, publicación y control de vigencia.",
    featured: true,
  },
  {
    icon: UsersIcon,
    title: "Registro de Internados",
    desc: "Internos, tutores, internados y rotaciones autorizadas entre IPRESS del mismo ámbito geográfico sanitario.",
    featured: false,
  },
  {
    icon: ActivityIcon,
    title: "Actividades docente-asistenciales",
    desc: "Registro y validación de actividades de los internos en sedes, con trazabilidad y subsanación.",
    featured: false,
  },
  {
    icon: ShieldCheckIcon,
    title: "Alcance institucional y roles",
    desc: "Acceso por JWT, gating por rol y auditoría. Cada entidad ve solo lo que le corresponde.",
    featured: false,
  },
];

const STEPS = [
  {
    n: "01",
    title: "Registra el convenio",
    desc: "Crea un convenio Marco o Específico y completa su evaluación técnica, opiniones y firmas hasta dejarlo vigente.",
  },
  {
    n: "02",
    title: "Registra el internado",
    desc: "Sobre un convenio Específico vigente, registra al interno y su tutor, dentro de tu ámbito institucional.",
  },
  {
    n: "03",
    title: "Autoriza rotaciones",
    desc: "Gestiona rotaciones entre IPRESS del mismo ámbito geográfico sanitario, con autorización de la autoridad del convenio.",
  },
  {
    n: "04",
    title: "Valida actividades",
    desc: "Registra las actividades docente-asistenciales y valídalas con trazabilidad completa del proceso.",
  },
];

const TESTIMONIALS = [
  {
    quote:
      "La trazabilidad de los convenios desde la solicitud hasta la vigencia nos ahorró semanas de seguimiento manual.",
    name: "Equipo DIGEP",
    role: "Dirección General de Personal de la Salud",
  },
  {
    quote:
      "Registrar internados sobre convenios vigentes y controlar las rotaciones por ámbito es directo y claro.",
    name: "Oficina Académica",
    role: "Universidad",
  },
  {
    quote:
      "Validar las actividades de los internos en la sede docente toma minutos y queda todo auditado.",
    name: "Tutor de sede",
    role: "IPRESS",
  },
  {
    quote:
      "El alcance por rol nos da la seguridad de que cada entidad accede únicamente a su información.",
    name: "OGAJ",
    role: "Asesoría jurídica",
  },
  {
    quote:
      "Las opiniones de CONAPRES y los campos clínicos quedan integrados en el mismo flujo del convenio.",
    name: "CONAPRES",
    role: "Comisión Nacional",
  },
];

const FOOTER_COLS = [
  {
    title: "Producto",
    links: [
      { label: "Módulos", href: "#features" },
      { label: "Cómo funciona", href: "#how" },
      { label: "Iniciar sesión", href: "/login" },
    ],
  },
  {
    title: "Módulos",
    links: [
      { label: "Convenios", href: "/login" },
      { label: "Internados", href: "/login" },
      { label: "Actividades", href: "/login" },
    ],
  },
  {
    title: "Recursos",
    links: [
      { label: "MINSA", href: "https://www.gob.pe/minsa" },
      { label: "Mesa de ayuda", href: "/login" },
      { label: "Documentación", href: "/login" },
    ],
  },
];

/* ───────────────────────── página ───────────────────────── */

export function Landing() {
  return (
    <div className="relative min-h-dvh overflow-x-clip bg-[var(--ld-bg)] text-[var(--ld-text)] [font-family:var(--font-source),system-ui,sans-serif]">
      {/* Fondo: mesh gradients + grid + noise */}
      <BackgroundFx />

      <Nav />
      <Hero />
      <LogosBar />
      <Features />
      <HowItWorks />
      <Testimonials />
      <FinalCta />
      <SiteFooter />
    </div>
  );
}

/* ── Fondo decorativo ── */
function BackgroundFx() {
  const reduced = useReducedMotion();
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10">
      {/* Mesh gradients animados */}
      <motion.div
        className="absolute -top-32 -left-24 h-[42rem] w-[42rem] rounded-full opacity-40 blur-3xl"
        style={{
          background:
            "radial-gradient(circle at center, var(--ld-secondary), transparent 60%)",
        }}
        animate={reduced ? undefined : { x: [0, 40, 0], y: [0, 30, 0] }}
        transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute top-1/3 -right-24 h-[36rem] w-[36rem] rounded-full opacity-30 blur-3xl"
        style={{
          background:
            "radial-gradient(circle at center, var(--ld-cta), transparent 60%)",
        }}
        animate={reduced ? undefined : { x: [0, -50, 0], y: [0, 40, 0] }}
        transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
      />
      {/* Grid sutil */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            "linear-gradient(var(--ld-text) 1px, transparent 1px), linear-gradient(90deg, var(--ld-text) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />
      {/* Noise SVG */}
      <div
        className="absolute inset-0 opacity-[0.035] mix-blend-multiply"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
        }}
      />
    </div>
  );
}

/* ── 1. Nav ── */
function Nav() {
  return (
    <motion.header
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="sticky top-0 z-50 w-full border-b border-[var(--ld-glass-border)] bg-[var(--ld-surface)] backdrop-blur-xl"
    >
      {/* Barra full width; el contenido se centra con un contenedor interno. */}
      <div className="mx-auto flex w-[min(72rem,94%)] items-center justify-between px-4 py-2.5">
        <a href="#top" className="flex items-center" aria-label="RENADS — inicio">
          <Image
            src="/logo-minsa.png"
            alt="Ministerio de Salud del Perú"
            width={2000}
            height={408}
            priority
            className="h-8 w-auto"
          />
        </a>

        <nav className="hidden items-center gap-6 text-sm md:flex">
          {NAV_LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="cursor-pointer text-[var(--ld-text)]/70 transition-colors hover:text-[var(--ld-text)]"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-1.5 text-[var(--ld-text)]">
          <ThemeToggle />
          <Link
            href="/login"
            className="cursor-pointer rounded-lg bg-[var(--ld-cta)] px-4 py-2 text-sm font-semibold text-white transition-all duration-200 hover:-translate-y-px hover:opacity-90"
          >
            Iniciar sesión
          </Link>
        </div>
      </div>
    </motion.header>
  );
}

/* ── 2. Hero ── */
function Hero() {
  const reduced = useReducedMotion();
  return (
    <section
      id="top"
      className="relative mx-auto grid min-h-[100dvh] w-[min(72rem,94%)] place-items-center py-20"
    >
      <ParticlesCanvas className="absolute inset-0 -z-10 h-full w-full" />

      <div className="grid w-full items-center gap-12 lg:grid-cols-2">
        {/* Texto */}
        <div className="text-center lg:text-left">
          <motion.span
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="inline-flex items-center gap-2 rounded-full border border-[var(--ld-primary)]/20 bg-[var(--ld-surface)] px-3 py-1 text-xs font-medium text-[var(--ld-primary)] backdrop-blur"
          >
            <span className="size-1.5 rounded-full bg-[var(--ld-cta)]" />
            MINSA · Perú
          </motion.span>

          <StaggerWords
            text="Registro Nacional de Articulación Docencia-Servicio en Salud"
            className="mt-5 text-4xl font-bold leading-[1.05] tracking-tight text-[var(--ld-text)] [font-family:var(--font-lexend)] sm:text-5xl lg:text-6xl"
          />

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8, duration: 0.6 }}
            className="mx-auto mt-6 max-w-xl text-lg text-[var(--ld-text)]/70 lg:mx-0"
          >
            Plataforma del MINSA para gestionar convenios, internados y actividades
            docente-asistenciales con trazabilidad total y alcance por institución.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1, duration: 0.6 }}
            className="mt-8 flex flex-col items-center gap-3 sm:flex-row lg:items-start"
          >
            <MagneticButton
              href="/login"
              className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-[var(--ld-cta)] px-6 py-3 font-semibold text-white shadow-lg shadow-[var(--ld-cta)]/20 transition-opacity hover:opacity-90"
            >
              Iniciar sesión
              <ArrowRightIcon className="size-4" />
            </MagneticButton>
            <a
              href="#features"
              className="inline-flex cursor-pointer items-center gap-2 rounded-lg border-2 border-[var(--ld-primary)] px-6 py-3 font-semibold text-[var(--ld-primary)] transition-colors hover:bg-[var(--ld-primary)]/5"
            >
              Conocer módulos
            </a>
          </motion.div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.2 }}
            className="mt-8 text-sm text-[var(--ld-text)]/55"
          >
            Usado por DIGEP, CONAPRES, OGAJ, universidades e IPRESS.
          </motion.p>
        </div>

        {/* Visual glass + floating badges */}
        <div className="relative mx-auto hidden h-[26rem] w-full max-w-md lg:block">
          <div
            className={`${GLASS} absolute inset-0 grid place-items-center overflow-hidden`}
          >
            {/* inner glow */}
            <div
              className="absolute inset-0 opacity-60"
              style={{
                background:
                  "radial-gradient(60% 50% at 50% 30%, var(--ld-secondary)22, transparent 70%)",
              }}
            />
            <div className="relative grid gap-3 p-8 text-center">
              <span className="text-6xl font-bold text-[var(--ld-primary)] [font-family:var(--font-lexend)]">
                100%
              </span>
              <span className="text-sm text-[var(--ld-text)]/70">
                Trazabilidad del proceso docencia-servicio
              </span>
            </div>
          </div>

          {[
            { label: "Convenios", top: "6%", left: "-6%", delay: 0 },
            { label: "Internados", top: "44%", left: "78%", delay: 0.6 },
            { label: "Actividades", top: "82%", left: "8%", delay: 1.2 },
          ].map((b) => (
            <motion.span
              key={b.label}
              style={{ top: b.top, left: b.left }}
              className={`${GLASS} absolute rounded-full px-4 py-2 text-sm font-medium text-[var(--ld-text)]`}
              animate={reduced ? undefined : { y: [0, -10, 0] }}
              transition={{
                duration: 4,
                repeat: Infinity,
                ease: "easeInOut",
                delay: b.delay,
              }}
            >
              {b.label}
            </motion.span>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── 3. Logos bar (marquee) ── */
function LogosBar() {
  const items = [...ENTIDADES, ...ENTIDADES];
  return (
    <div className="relative overflow-hidden py-10">
      <div className="flex w-max animate-[marquee_28s_linear_infinite] gap-12 opacity-30">
        {items.map((e, i) => (
          <span
            key={i}
            className="text-lg font-semibold whitespace-nowrap text-[var(--ld-text)] [font-family:var(--font-lexend)]"
          >
            {e}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ── 4. Features ── */
function Features() {
  return (
    <Reveal
      id="features"
      className="mx-auto w-[min(72rem,94%)] py-20"
    >
      <motion.div variants={revealItem} className="mb-12 text-center">
        <h2 className="text-3xl font-bold text-[var(--ld-text)] [font-family:var(--font-lexend)] sm:text-4xl">
          Tres módulos, un solo registro
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-[var(--ld-text)]/70">
          Del convenio a la actividad validada, todo el proceso docencia-servicio
          en una plataforma.
        </p>
      </motion.div>

      <div className="grid gap-5 md:grid-cols-3">
        {FEATURES.map((f) => (
          <motion.article
            key={f.title}
            variants={revealItem}
            className={`${GLASS} group p-6 transition-transform duration-200 hover:-translate-y-1 ${
              f.featured ? "md:col-span-2" : ""
            }`}
          >
            <span className="grid size-11 place-items-center rounded-xl bg-[var(--ld-primary)]/10 text-[var(--ld-primary)]">
              <f.icon className="size-5" />
            </span>
            <h3 className="mt-4 text-lg font-semibold text-[var(--ld-text)] [font-family:var(--font-lexend)]">
              {f.title}
            </h3>
            <p className="mt-2 text-sm text-[var(--ld-text)]/70">{f.desc}</p>
          </motion.article>
        ))}
      </div>
    </Reveal>
  );
}

/* ── 5. How it works ── */
function HowItWorks() {
  return (
    <Reveal id="how" className="mx-auto w-[min(64rem,94%)] py-20">
      <motion.div variants={revealItem} className="mb-14 text-center">
        <h2 className="text-3xl font-bold text-[var(--ld-text)] [font-family:var(--font-lexend)] sm:text-4xl">
          Cómo funciona
        </h2>
      </motion.div>

      <div className="grid gap-8">
        {STEPS.map((s, i) => (
          <motion.div
            key={s.n}
            variants={revealItem}
            className={`flex flex-col items-center gap-6 md:flex-row ${
              i % 2 === 1 ? "md:flex-row-reverse" : ""
            }`}
          >
            <div className={`${GLASS} grid size-24 shrink-0 place-items-center`}>
              <span className="text-3xl font-bold text-[var(--ld-primary)] [font-family:var(--font-lexend)]">
                {s.n}
              </span>
            </div>
            <div
              className={`text-center md:flex-1 ${
                i % 2 === 1 ? "md:text-right" : "md:text-left"
              }`}
            >
              <h3 className="text-xl font-semibold text-[var(--ld-text)] [font-family:var(--font-lexend)]">
                {s.title}
              </h3>
              <p className="mt-2 text-[var(--ld-text)]/70">{s.desc}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </Reveal>
  );
}

/* ── 6. Testimonials (masonry + tilt) ── */
function Testimonials() {
  return (
    <Reveal
      id="testimonials"
      className="mx-auto w-[min(72rem,94%)] py-20"
    >
      <motion.div variants={revealItem} className="mb-12 text-center">
        <h2 className="text-3xl font-bold text-[var(--ld-text)] [font-family:var(--font-lexend)] sm:text-4xl">
          Lo que dicen las instituciones
        </h2>
      </motion.div>

      <div className="columns-1 gap-5 sm:columns-2 lg:columns-3 [&>*]:mb-5">
        {TESTIMONIALS.map((t, i) => (
          <motion.div key={i} variants={revealItem} className="break-inside-avoid">
            <TiltCard className={`${GLASS} p-6`}>
              <p className="text-[var(--ld-text)]/85">“{t.quote}”</p>
              <div className="mt-4">
                <p className="font-semibold text-[var(--ld-text)] [font-family:var(--font-lexend)]">
                  {t.name}
                </p>
                <p className="text-sm text-[var(--ld-text)]/60">{t.role}</p>
              </div>
            </TiltCard>
          </motion.div>
        ))}
      </div>
    </Reveal>
  );
}

/* ── 7. CTA final ── */
function FinalCta() {
  return (
    <section className="mx-auto w-[min(72rem,94%)] py-20">
      <div className="relative overflow-hidden rounded-3xl p-[2px]">
        {/* borde gradiente rotatorio */}
        <motion.div
          aria-hidden
          className="absolute inset-[-100%]"
          style={{
            background:
              "conic-gradient(from 0deg, var(--ld-primary), var(--ld-cta), var(--ld-secondary), var(--ld-primary))",
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 12, repeat: Infinity, ease: "linear" }}
        />
        <div className="relative grid gap-6 rounded-3xl bg-[var(--ld-surface-strong)] p-10 backdrop-blur-xl md:grid-cols-2 md:items-center">
          <div>
            <h2 className="text-3xl font-bold text-[var(--ld-text)] [font-family:var(--font-lexend)]">
              Solicita acceso a RENADS
            </h2>
            <p className="mt-3 text-[var(--ld-text)]/70">
              Deja tu correo institucional y el equipo del MINSA te contactará
              para habilitar tu acceso.
            </p>
          </div>
          <form
            className="flex flex-col gap-3 sm:flex-row"
            onSubmit={(e) => e.preventDefault()}
          >
            <input
              type="email"
              required
              placeholder="tu.correo@institucion.gob.pe"
              aria-label="Correo institucional"
              className="w-full rounded-lg border border-[var(--ld-primary)]/20 bg-[var(--ld-input)] px-4 py-3 text-base text-[var(--ld-text)] outline-none transition-shadow focus:ring-3 focus:ring-[var(--ld-primary)]/20"
            />
            <button
              type="submit"
              className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-lg bg-[var(--ld-cta)] px-6 py-3 font-semibold whitespace-nowrap text-white transition-all duration-200 hover:-translate-y-px hover:opacity-90"
            >
              Solicitar acceso
              <CheckIcon className="size-4" />
            </button>
          </form>
        </div>
      </div>
    </section>
  );
}

/* ── 8. Footer ── */
function SocialIcon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden className="size-5">
      <path d={d} />
    </svg>
  );
}

function SiteFooter() {
  const socials = [
    {
      label: "Facebook",
      href: "https://www.facebook.com/minsaperu",
      d: "M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z",
    },
    {
      label: "X",
      href: "https://x.com/Minsa_Peru",
      d: "M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z",
    },
    {
      label: "YouTube",
      href: "https://www.youtube.com/@MinsaPeruSalud",
      d: "M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z",
    },
  ];

  return (
    <footer className="border-t border-[var(--ld-text)]/10 bg-[var(--ld-surface)] backdrop-blur-sm">
      <div className="mx-auto grid w-[min(72rem,94%)] gap-10 py-14 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <span className="font-bold [font-family:var(--font-lexend)] text-[var(--ld-text)]">
            RENADS
          </span>
          <p className="mt-3 max-w-xs text-sm text-[var(--ld-text)]/60">
            Registro Nacional de Articulación Docencia-Servicio en Salud —
            Ministerio de Salud del Perú.
          </p>
        </div>

        {FOOTER_COLS.map((col) => (
          <div key={col.title}>
            <h3 className="text-sm font-semibold text-[var(--ld-text)] [font-family:var(--font-lexend)]">
              {col.title}
            </h3>
            <ul className="mt-4 grid gap-2 text-sm">
              {col.links.map((l) => (
                <li key={l.label}>
                  <a
                    href={l.href}
                    className="cursor-pointer text-[var(--ld-text)]/60 transition-colors hover:text-[var(--ld-text)]"
                  >
                    {l.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="border-t border-[var(--ld-text)]/10">
        <div className="mx-auto flex w-[min(72rem,94%)] flex-col items-center justify-between gap-4 py-6 text-sm text-[var(--ld-text)]/60 sm:flex-row">
          <p>© {new Date().getFullYear()} RENADS · Ministerio de Salud del Perú.</p>
          <nav
            className="flex items-center gap-2"
            aria-label="Redes sociales del Ministerio de Salud"
          >
            {socials.map((s) => (
              <a
                key={s.label}
                href={s.href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={s.label}
                className="grid size-9 cursor-pointer place-items-center rounded-lg text-[var(--ld-text)]/60 transition-all duration-200 hover:text-[var(--ld-cta)] hover:shadow-[0_0_18px_var(--ld-cta)]"
              >
                <SocialIcon d={s.d} />
              </a>
            ))}
          </nav>
        </div>
      </div>
    </footer>
  );
}
