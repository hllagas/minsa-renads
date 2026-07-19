"use client";

import { useEffect, useRef } from "react";
import { useReducedMotion } from "framer-motion";

interface Point {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

/**
 * Red de partículas flotantes conectadas por líneas, reactivas al mouse.
 * Se dibuja sobre un <canvas> absoluto que llena a su contenedor. Respeta reduced-motion.
 */
export function ParticlesCanvas({
  className,
  color = "37, 99, 235", // --color-primary (#2563EB) en RGB
  density = 120,
}: {
  className?: string;
  color?: string;
  density?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = 0;
    let height = 0;
    let raf = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const points: Point[] = [];
    const mouse = { x: -9999, y: -9999 };
    const LINK_DIST = 130;
    const MOUSE_LINK_DIST = 200; // radio de conexión cursor→puntos

    // Color de la red: sigue a `--ld-primary` (cambia con claro/oscuro); cae al prop.
    let colorRGB = color;
    function hexToRgb(hex: string): string | null {
      const m = hex.trim().match(/^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i);
      if (!m) return null;
      return `${parseInt(m[1], 16)}, ${parseInt(m[2], 16)}, ${parseInt(m[3], 16)}`;
    }
    function resolveColor() {
      const v = getComputedStyle(canvas!).getPropertyValue("--ld-primary");
      colorRGB = (v && hexToRgb(v)) || color;
    }
    resolveColor();

    function resize() {
      const parent = canvas!.parentElement;
      width = parent?.clientWidth ?? window.innerWidth;
      height = parent?.clientHeight ?? window.innerHeight;
      canvas!.width = width * dpr;
      canvas!.height = height * dpr;
      canvas!.style.width = `${width}px`;
      canvas!.style.height = `${height}px`;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function seed() {
      points.length = 0;
      // Densidad acotada según área (entre 80 y `density`).
      const count = Math.min(
        density,
        Math.max(80, Math.round((width * height) / 14000)),
      );
      for (let i = 0; i < count; i++) {
        points.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.5) * 0.35,
          vy: (Math.random() - 0.5) * 0.35,
        });
      }
    }

    function draw() {
      ctx!.clearRect(0, 0, width, height);

      for (const p of points) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;

        // Repulsión suave del cursor.
        const dx = p.x - mouse.x;
        const dy = p.y - mouse.y;
        const dist2 = dx * dx + dy * dy;
        if (dist2 < 120 * 120) {
          const d = Math.sqrt(dist2) || 1;
          p.x += (dx / d) * 0.6;
          p.y += (dy / d) * 0.6;
        }
      }

      // Líneas de conexión entre puntos.
      for (let i = 0; i < points.length; i++) {
        for (let j = i + 1; j < points.length; j++) {
          const a = points[i];
          const b = points[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = Math.hypot(dx, dy);
          if (dist < LINK_DIST) {
            const alpha = (1 - dist / LINK_DIST) * 0.35;
            ctx!.strokeStyle = `rgba(${colorRGB}, ${alpha})`;
            ctx!.lineWidth = 1;
            ctx!.beginPath();
            ctx!.moveTo(a.x, a.y);
            ctx!.lineTo(b.x, b.y);
            ctx!.stroke();
          }
        }
      }

      // Líneas cursor→puntos cercanos: la red "responde" al mouse.
      if (mouse.x > -9998) {
        for (const p of points) {
          const dx = p.x - mouse.x;
          const dy = p.y - mouse.y;
          const dist = Math.hypot(dx, dy);
          if (dist < MOUSE_LINK_DIST) {
            const alpha = (1 - dist / MOUSE_LINK_DIST) * 0.5;
            ctx!.strokeStyle = `rgba(${colorRGB}, ${alpha})`;
            ctx!.lineWidth = 1.1;
            ctx!.beginPath();
            ctx!.moveTo(mouse.x, mouse.y);
            ctx!.lineTo(p.x, p.y);
            ctx!.stroke();
          }
        }
      }

      // Puntos con glow suave.
      ctx!.shadowColor = `rgba(${colorRGB}, 0.8)`;
      ctx!.shadowBlur = 6;
      for (const p of points) {
        ctx!.fillStyle = `rgba(${colorRGB}, 0.6)`;
        ctx!.beginPath();
        ctx!.arc(p.x, p.y, 1.6, 0, Math.PI * 2);
        ctx!.fill();
      }
      ctx!.shadowBlur = 0;

      raf = requestAnimationFrame(draw);
    }

    function onMouseMove(e: MouseEvent) {
      const rect = canvas!.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
    }
    function onMouseLeave() {
      mouse.x = -9999;
      mouse.y = -9999;
    }

    resize();
    seed();

    if (reduced) {
      // Sin animación: una sola pasada estática.
      draw();
      cancelAnimationFrame(raf);
    } else {
      raf = requestAnimationFrame(draw);
    }

    const onResize = () => {
      resize();
      seed();
    };
    window.addEventListener("resize", onResize);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseleave", onMouseLeave);

    // Recolorear al alternar claro/oscuro (cambia la clase .dark en <html>).
    const themeObserver = new MutationObserver(resolveColor);
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    return () => {
      cancelAnimationFrame(raf);
      themeObserver.disconnect();
      window.removeEventListener("resize", onResize);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseleave", onMouseLeave);
    };
  }, [color, density, reduced]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className={className}
    />
  );
}
