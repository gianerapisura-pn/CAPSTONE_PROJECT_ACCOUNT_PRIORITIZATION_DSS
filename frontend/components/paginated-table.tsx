"use client";

import { useState, type ReactNode } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

export function PaginatedTable<Row>({ rows, label, children, initialPage = 1 }: {
  rows: Row[]; label: string; children: (visible: Row[], start: number) => ReactNode; initialPage?: number;
}) {
  const [page, setPage] = useState(initialPage);
  const pageSize = 10;
  const pages = Math.max(1, Math.ceil(rows.length / pageSize));
  const currentPage = Math.min(page, pages);
  const start = (currentPage - 1) * pageSize;
  return <>
    {children(rows.slice(start, start + pageSize), start)}
    {!rows.length && <p className="native-note">No results are available for this run.</p>}
    <nav className="pagination" aria-label={`${label} pagination`}>
      <span aria-live="polite">Showing {rows.length ? start + 1 : 0}-{Math.min(start + pageSize, rows.length)} of {rows.length}</span>
      <div><button className="icon-button" aria-label={`Previous ${label} page`} title="Previous page" disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}><ChevronLeft /></button><span>Page {currentPage} of {pages}</span><button className="icon-button" aria-label={`Next ${label} page`} title="Next page" disabled={currentPage >= pages} onClick={() => setPage(currentPage + 1)}><ChevronRight /></button></div>
    </nav>
  </>;
}
