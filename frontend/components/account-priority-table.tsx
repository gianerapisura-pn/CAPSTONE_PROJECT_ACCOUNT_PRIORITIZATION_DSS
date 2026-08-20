"use client";

import { Download, Search } from "lucide-react";
import { useMemo, useState } from "react";
import type { AccountPriority } from "@/types/dss";

export function AccountPriorityTable({ rows }: { rows: AccountPriority[] }) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(
    () => rows.filter((row) => row.account.toLowerCase().includes(query.toLowerCase())).sort((a, b) => a.priorityRank - b.priorityRank || a.account.localeCompare(b.account)),
    [rows, query]
  );

  return (
    <section className="panel">
      <div className="toolbar" style={{ gridTemplateColumns: "1fr auto", alignItems: "center" }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Search size={18} />
          <input aria-label="Search accounts" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search accounts" />
        </label>
        <button className="button secondary" type="button">
          <Download size={18} />
          Export
        </button>
      </div>
      <div className="table-wrap" style={{ marginTop: 16 }}>
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Account</th>
              <th>Priority Group</th>
              <th>Final Priority Score</th>
              <th>RFM</th>
              <th>Settlement Days</th>
              <th>Inactivity Risk</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((row) => (
              <tr key={row.account}>
                <td>{row.priorityRank}</td>
                <td>{row.account}</td>
                <td><span className={`badge ${row.priorityGroup.toLowerCase()}`}>{row.priorityGroup}</span></td>
                <td>{row.finalPriorityScore.toFixed(4)}</td>
                <td>{row.rfmScore.toFixed(2)}</td>
                <td>{row.settlementDaysAvg.toFixed(1)}</td>
                <td>{row.inactivityRisk ?? "Unavailable"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
