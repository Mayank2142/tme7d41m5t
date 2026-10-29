import { useCallback, useEffect, useState } from "react";

export type View = "decision" | "accuracy" | "methodology";
export interface Filters {
  date: string;
  from: string;
  to: string;
  cutoff: string;
  release: string;
}
export const SHA = /^[a-f0-9]{64}$/;
export const JANUARY = /^2026-01-(0[1-9]|[12][0-9]|3[01])$/;
export const CUTOFF = /^([01][0-9]|2[0-3]):[0-5][0-9]$/;
export function viewFor(path: string): View {
  return path === "/accuracy" ? "accuracy" : path === "/methodology" ? "methodology" : "decision";
}
export function selectionError(view: View, filters: Filters): string | null {
  if (!SHA.test(filters.release)) return "Choose a valid accepted dataset release.";
  if (!CUTOFF.test(filters.cutoff)) return "Enter a desk cutoff in HH:MM, from 00:00 to 23:59.";
  if (!JANUARY.test(filters.date))
    return view === "decision"
      ? "Choose a purchase decision date in January 2026."
      : "The saved decision date must be in January 2026.";
  if (!JANUARY.test(filters.from) || !JANUARY.test(filters.to))
    return "Both purchase decision dates must be in January 2026.";
  if (filters.from > filters.to) return "The end date must be on or after the start date.";
  return null;
}
export function selectionFrom(location: string, release: string, cutoff: string) {
  const url = new URL(location, "http://workbench.local");
  const view = viewFor(url.pathname);
  const params = url.searchParams;
  const filters: Filters = {
    date: params.get("decision_date") ?? "2026-01-31",
    from: params.get("decision_from") ?? "2026-01-01",
    to: params.get("decision_to") ?? "2026-01-31",
    cutoff: params.get("cutoff_local") ?? cutoff,
    release: params.get("release_id") ?? release,
  };
  const allowed = new Set([
    "cutoff_local",
    "release_id",
    "decision_date",
    "decision_from",
    "decision_to",
  ]);
  let problem: string | null = null;
  for (const key of params.keys()) {
    if (!allowed.has(key) || params.getAll(key).length !== 1)
      problem =
        "The address contains unsupported or repeated filters. Reset the selection or apply corrected filters.";
  }
  return { view, filters, problem: problem ?? selectionError(view, filters) };
}
export function hrefFor(view: View, filters: Filters): string {
  const params = new URLSearchParams({ cutoff_local: filters.cutoff, release_id: filters.release });
  params.set("decision_date", filters.date);
  params.set("decision_from", filters.from);
  params.set("decision_to", filters.to);
  return `/${view}?${params}`;
}
const current = () => window.location.pathname + window.location.search;
export function useLocation() {
  const [location, setLocation] = useState(current);
  useEffect(() => {
    const changed = () => setLocation(current());
    window.addEventListener("popstate", changed);
    return () => window.removeEventListener("popstate", changed);
  }, []);
  const navigate = useCallback((href: string, replace = false) => {
    if (href !== window.location.pathname + window.location.search) {
      window.history[replace ? "replaceState" : "pushState"](null, "", href);
      setLocation(href);
    }
  }, []);
  return { location, navigate };
}
