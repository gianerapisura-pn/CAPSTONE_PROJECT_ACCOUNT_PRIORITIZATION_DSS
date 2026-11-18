import type { ReactNode } from "react";
import { ExplainedValue, resultExplanation } from "@/components/result-explanation";

/** Saved evidence needs its own population and comparison, not account-detail help. */
export function ValidationValue({ metric, context, label, definition, calculation, note, children }: {
  metric: string;
  context: string;
  label?: string;
  definition?: string;
  calculation?: string;
  note?: string;
  children: ReactNode;
}) {
  const base = resultExplanation(metric);
  return <ExplainedValue explanation={{
    title: `${context}: ${label ?? base.title}${typeof children === "string" || typeof children === "number" ? ` (${children})` : ""}`,
    basis: definition ?? base.basis,
    calculation: calculation ?? (definition ? undefined : base.calculation),
    note: note ?? base.note,
  }}>{children}</ExplainedValue>;
}
