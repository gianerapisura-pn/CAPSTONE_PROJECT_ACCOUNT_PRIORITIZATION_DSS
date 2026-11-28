"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ExplainedValue } from "@/components/result-explanation";
import type { SalesChange } from "@/components/sales-change-report";

type Comparison = NonNullable<SalesChange["comparison"]>;
const money = new Intl.NumberFormat("en-PH", { style: "currency", currency: "PHP", maximumFractionDigits: 2 });
const shortMoney = new Intl.NumberFormat("en-PH", { style: "currency", currency: "PHP", notation: "compact", maximumFractionDigits: 2 });
const axisNumber = new Intl.NumberFormat("en-PH", { notation: "compact", maximumSignificantDigits: 3 });

export function purchasingGroupLabel(group: string, comparison: Pick<Comparison, "previous_year" | "current_year">) {
  return group === "Previous year only" ? `Purchased only in ${comparison.previous_year}`
    : group === "Current year only" ? `Purchased only in ${comparison.current_year}`
      : group === "Purchased in both years" || group === "Both years" ? "Purchased in both years" : group;
}

/** One shared linear axis, including zero, for all purchasing-group contributions. */
export function contributionScale(values: number[]) {
  const largest = Math.max(0, ...values.map(Math.abs));
  if (!largest) return { minimum: -1, maximum: 1, zero: 50, ticks: [0] };
  const base = 10 ** Math.floor(Math.log10(largest / 4));
  const step = ([1, 2, 5, 10].find(multiplier => multiplier * base >= largest / 4) ?? 10) * base;
  const minimum = Math.floor(Math.min(0, ...values) / step) * step;
  const maximum = Math.ceil(Math.max(0, ...values) / step) * step;
  const span = maximum - minimum;
  return { minimum, maximum, zero: -minimum / span * 100,
    ticks: Array.from({ length: Math.round(span / step) + 1 }, (_, index) => minimum + index * step) };
}

export function SalesComparisonCharts({ comparison: c }: { comparison: Comparison }) {
  const [trigger, setTrigger] = useState<"hover" | "click">("hover");
  const annual = [
    { year: String(c.previous_year), sales: Number(c.previous_total) },
    { year: String(c.current_year), sales: Number(c.current_total) },
  ];
  const scale = contributionScale(c.groups.map(group => Number(group.change)));
  const position = (value: number) => (value - scale.minimum) / (scale.maximum - scale.minimum) * 100;
  return <div className="sales-comparison-charts">
    <section className="sales-chart-card" aria-label="Annual sales comparison">
      <h3>1. Annual sales comparison</h3>
      <p className="native-note">Compare the total accepted Sales Invoice value in each complete year. Both bars start at zero.</p>
      <div className="sales-annual-chart" role="img" aria-label={`Annual sales: ${c.previous_year}: ${money.format(Number(c.previous_total))}; ${c.current_year}: ${money.format(Number(c.current_total))}. Both bars start at zero.`}
        onPointerDownCapture={event => setTrigger(event.pointerType === "touch" ? "click" : "hover")}
        onPointerMoveCapture={event => { if (event.pointerType === "mouse" && trigger !== "hover") setTrigger("hover"); }}>
        <p className="native-note">Sales (PHP)</p>
        <ResponsiveContainer width="100%" height={290}><BarChart data={annual} margin={{ top: 34, right: 16, bottom: 12, left: 0 }} accessibilityLayer>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="year" tickMargin={12} height={42} tick={{ fontSize: 12 }} />
          <YAxis domain={[0, "auto"]} width={52} tick={{ fontSize: 11 }} tickFormatter={value => axisNumber.format(Number(value))} />
          <Tooltip trigger={trigger} cursor={{ fill: "#eef4f8" }} allowEscapeViewBox={{ x: false, y: false }} wrapperStyle={{ maxWidth: "min(280px, calc(100vw - 48px))", whiteSpace: "normal", zIndex: 20 }} content={({ active, payload }) => {
            const row = payload?.[0]?.payload as typeof annual[number] | undefined;
            return active && row ? <div className="native-result-tooltip sales-chart-tooltip" role="tooltip"><strong>{row.year} sales</strong><p>{money.format(row.sales)} in accepted Sales Invoices.</p><p>{row.year === String(c.previous_year) ? "The earlier-year total used as the starting point for this comparison." : "The later-year total compared with the earlier year."} Invoices are counted once, regardless of the number of collection rows.</p></div> : null;
          }} />
          <Bar dataKey="sales" name="Annual sales" fill="#4d78ac" maxBarSize={180} isAnimationActive={false}>
            <LabelList dataKey="sales" position="top" offset={10} formatter={value => shortMoney.format(Number(value))} fill="#263c4a" fontSize={12} />
          </Bar>
        </BarChart></ResponsiveContainer>
      </div>
    </section>
    <section className="sales-chart-card" aria-label="Purchasing group contributions">
      <h3>2. Which purchasing groups added or reduced sales?</h3>
      <p className="native-note">Red extends left from zero for a decrease; green extends right for an increase. All rows use the same scale. Hover, focus, or tap a row for its explanation.</p>
      <div className="sales-contribution-chart" aria-label={`Contribution to the sales change from ${c.previous_year} to ${c.current_year}`}>
        {c.groups.map(group => {
          const change = Number(group.change);
          const end = position(change);
          const members = c.accounts.filter(account => account.group === group.group);
          const before = members.reduce((sum, account) => sum + Number(account.previous_sales), 0);
          const after = members.reduce((sum, account) => sum + Number(account.current_sales), 0);
          const label = purchasingGroupLabel(group.group, c);
          const reading = change === 0 ? "did not change the combined sales total" : `${change < 0 ? "reduced" : "added to"} the combined sales total by ${money.format(Math.abs(change))}`;
          return <ExplainedValue key={group.group} inline={false} className="sales-contribution-row" explanation={{ title: label, compact: true,
            interpretation: `${group.account_count} ${group.account_count === 1 ? "account" : "accounts"} ${reading}: ${money.format(before)} in ${c.previous_year} and ${money.format(after)} in ${c.current_year}.`,
            basis: group.group === "Previous year only" ? `These accounts purchased in ${c.previous_year} but had no accepted SI sales in ${c.current_year}.` : group.group === "Current year only" ? `These accounts purchased in ${c.current_year} but had no accepted SI sales in ${c.previous_year}.` : "These accounts purchased in both selected complete years.",
            calculation: `${money.format(after)} minus ${money.format(before)} = ${money.format(change)}.`, note: "The purchasing pattern does not establish account closure, acquisition, or the cause of the change." }}>
            <span className="sales-contribution-name">{label}</span>
            <span className="sales-contribution-track" data-value={change} data-zero={scale.zero} aria-hidden="true">
              <span className="sales-contribution-zero" style={{ left: `${scale.zero}%` }} />
              <span className={`sales-contribution-bar ${change < 0 ? "decrease" : change > 0 ? "increase" : "unchanged"}`} style={{ left: `${Math.min(scale.zero, end)}%`, width: `${Math.abs(end - scale.zero)}%` }} />
            </span>
            <span className="sales-contribution-amount">{change > 0 ? "+" : ""}{money.format(change)}</span>
          </ExplainedValue>;
        })}
        <div className="sales-contribution-axis" aria-hidden="true"><span className="sales-contribution-ticks">{scale.ticks.map((tick, index) => <span key={tick} className={index === 0 && scale.ticks.length > 1 ? "first" : index === scale.ticks.length - 1 && scale.ticks.length > 1 ? "last" : ""} style={{ left: `${position(tick)}%` }}>{tick > 0 ? "+" : ""}{axisNumber.format(tick)}</span>)}</span></div>
      </div>
      <p className="native-note">Change in sales (PHP). The three contributions together equal the annual sales change; they do not explain its cause.</p>
    </section>
  </div>;
}
