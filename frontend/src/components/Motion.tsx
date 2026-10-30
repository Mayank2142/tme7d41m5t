import { type HTMLAttributes, useEffect, useRef } from "react";

const motionPreference = "(prefers-reduced-motion: no-preference)";

/** Decorative effects retain the system cursor and never receive pointer events. */
export function MotionEffects() {
  const cursor = useRef<HTMLDivElement>(null);
  const ring = useRef<HTMLSpanElement>(null);
  const dot = useRef<HTMLSpanElement>(null);
  const progress = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const bar = progress.current;
    if (!bar || typeof window.requestAnimationFrame !== "function") return;
    let frame = 0;
    function update() {
      frame = 0;
      const distance = document.documentElement.scrollHeight - window.innerHeight;
      const position = distance > 0 ? Math.min(1, Math.max(0, window.scrollY / distance)) : 0;
      bar?.style.setProperty("--scroll-progress", String(position));
    }
    function schedule() {
      if (!frame) frame = window.requestAnimationFrame(update);
    }
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(schedule);
    observer?.observe(document.documentElement);
    schedule();
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      observer?.disconnect();
    };
  }, []);

  useEffect(() => {
    const overlay = cursor.current;
    const halo = ring.current;
    const point = dot.current;
    if (
      !overlay ||
      !halo ||
      !point ||
      typeof window.matchMedia !== "function" ||
      typeof window.requestAnimationFrame !== "function"
    )
      return;
    const preference = window.matchMedia(
      `(hover: hover) and (pointer: fine) and ${motionPreference}`,
    );
    const nodes = { overlay, halo, point };
    let frame = 0;
    let visible = false;
    let x = 0;
    let y = 0;
    let smoothX = 0;
    let smoothY = 0;
    let lastFrame = 0;

    function hide() {
      visible = false;
      nodes.overlay.dataset.visible = "false";
      nodes.overlay.dataset.pressed = "false";
      window.cancelAnimationFrame(frame);
      frame = 0;
      lastFrame = 0;
    }
    function draw(timestamp: number) {
      frame = 0;
      if (!visible) return;
      // Time-based damping keeps the same gentle trail on 60 Hz and faster screens.
      const elapsed = lastFrame ? Math.min(timestamp - lastFrame, 64) : 1000 / 60;
      const blend = 1 - Math.exp(-elapsed / 140);
      lastFrame = timestamp;
      smoothX += (x - smoothX) * blend;
      smoothY += (y - smoothY) * blend;
      nodes.halo.style.transform = `translate3d(${smoothX}px, ${smoothY}px, 0)`;
      nodes.point.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      if (Math.hypot(x - smoothX, y - smoothY) > 0.1) frame = window.requestAnimationFrame(draw);
      else lastFrame = 0;
    }
    function move(event: PointerEvent) {
      const target = event.target instanceof Element ? event.target : null;
      if (
        !preference.matches ||
        event.pointerType !== "mouse" ||
        target?.closest("input, textarea, select, [contenteditable]:not([contenteditable=false])")
      ) {
        hide();
        return;
      }
      x = event.clientX;
      y = event.clientY;
      if (!visible) {
        smoothX = x;
        smoothY = y;
      }
      visible = true;
      nodes.overlay.dataset.visible = "true";
      nodes.overlay.dataset.interactive = String(
        Boolean(target?.closest("a, button:enabled, summary")),
      );
      if (!frame) frame = window.requestAnimationFrame(draw);
    }
    function press() {
      nodes.overlay.dataset.pressed = "true";
    }
    function release() {
      nodes.overlay.dataset.pressed = "false";
    }
    function leave(event: PointerEvent) {
      if (!event.relatedTarget) hide();
    }
    function preferenceChanged() {
      if (!preference.matches) hide();
    }
    window.addEventListener("pointermove", move, { passive: true });
    window.addEventListener("pointerdown", press, { passive: true });
    window.addEventListener("pointerup", release, { passive: true });
    window.addEventListener("pointerout", leave, { passive: true });
    window.addEventListener("blur", hide);
    window.addEventListener("keydown", hide);
    document.addEventListener("visibilitychange", hide);
    preference.addEventListener("change", preferenceChanged);
    return () => {
      hide();
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerdown", press);
      window.removeEventListener("pointerup", release);
      window.removeEventListener("pointerout", leave);
      window.removeEventListener("blur", hide);
      window.removeEventListener("keydown", hide);
      document.removeEventListener("visibilitychange", hide);
      preference.removeEventListener("change", preferenceChanged);
    };
  }, []);

  return (
    <>
      <div ref={progress} className="scroll-progress" aria-hidden="true" />
      <div ref={cursor} className="cursor-effect" data-visible="false" aria-hidden="true">
        <span ref={ring} className="cursor-ring" />
        <span ref={dot} className="cursor-dot" />
      </div>
    </>
  );
}

/** Reveal once on entry; content stays visible if motion or observation is unavailable. */
export function MotionRegion({ children, ...props }: HTMLAttributes<HTMLDivElement>) {
  const region = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const scope = region.current;
    if (
      !scope ||
      typeof window.matchMedia !== "function" ||
      typeof IntersectionObserver === "undefined" ||
      typeof Element.prototype.animate !== "function"
    )
      return;
    const preference = window.matchMedia(motionPreference);
    const animations = new Set<Animation>();
    let observer: IntersectionObserver | null = null;
    let disposed = false;
    function reset() {
      observer?.disconnect();
      observer = null;
      for (const animation of animations) animation.cancel();
      animations.clear();
    }
    function setup() {
      reset();
      if (!preference.matches || !scope) return;
      observer = new IntersectionObserver(
        (entries) => {
          if (disposed || !preference.matches) return;
          let order = 0;
          for (const entry of entries) {
            if (!entry.isIntersecting) continue;
            observer?.unobserve(entry.target);
            const animation = entry.target.animate(
              [
                { opacity: 0, transform: "translateY(12px)" },
                { opacity: 1, transform: "translateY(0)" },
              ],
              {
                duration: 850,
                delay: Math.min(order++ * 85, 255),
                easing: "cubic-bezier(.22,.61,.36,1)",
              },
            );
            animations.add(animation);
            animation.finished.then(() => animations.delete(animation)).catch(() => {});
          }
        },
        { threshold: 0.08 },
      );
      for (const element of scope.querySelectorAll(".metric, .panel:not(details)"))
        observer.observe(element);
    }
    setup();
    preference.addEventListener("change", setup);
    return () => {
      disposed = true;
      reset();
      preference.removeEventListener("change", setup);
    };
  }, []);
  return (
    <div ref={region} {...props}>
      {children}
    </div>
  );
}
