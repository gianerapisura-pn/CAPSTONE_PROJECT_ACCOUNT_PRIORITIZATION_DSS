import type { ReactNode } from "react";
import { ExplainedValue, resultExplanation } from "@/components/result-explanation";
import { displayedNumber, evidenceInterpretation, scalarInterpretation } from "@/lib/result-interpretation";

/** Saved evidence needs its own population and comparison, not account-detail help. */
export function ValidationValue({ metric, context, label, definition, calculation, note, children, evidence, peers, interpretation, rawValue }: {
  metric: string;
  context: string;
  label?: string;
  definition?: string;
  calculation?: string;
  note?: string;
  children: ReactNode;
  evidence?: Record<string, unknown>;
  peers?: readonly Record<string, unknown>[];
  interpretation?: string;
  rawValue?: unknown;
}) {
  const base = resultExplanation(metric);
  const value = typeof children === "number" ? children : typeof children === "string" ? displayedNumber(children) : undefined;
  const number = typeof rawValue === "number" && Number.isFinite(rawValue) ? rawValue : undefined;
  const reading = interpretation ?? (evidence ? evidenceInterpretation(metric, evidence, peers, number) : undefined) ?? scalarInterpretation(metric, number ?? value) ?? definition;
  return <ExplainedValue explanation={{
    title: `${context}: ${label ?? base.title}${typeof children === "string" || typeof children === "number" ? ` (${children})` : ""}`,
    basis: definition ?? base.basis,
    calculation: calculation ?? (definition ? undefined : base.calculation),
    note: note ?? base.note,
    interpretation: reading ?? base.basis,
    compact: true,
  }}>{children}</ExplainedValue>;
}
