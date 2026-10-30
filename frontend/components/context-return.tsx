import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { safeReportReturn } from "@/lib/report-navigation";

export function ContextReturn({ value }: { value: string | null | undefined }) {
  const destination = safeReportReturn(value);
  return destination ? <nav className="context-return" aria-label="Return to originating insight"><Link className="back-link" href={destination.href}><ArrowLeft size={16} />{destination.label}</Link></nav> : null;
}
