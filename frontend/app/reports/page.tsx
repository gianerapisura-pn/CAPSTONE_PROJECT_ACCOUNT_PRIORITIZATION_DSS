export default function ReportsPage() {
  const reportUrl = process.env.NEXT_PUBLIC_POWER_BI_REPORT_URL;
  return (
    <div className="grid">
      <header>
        <h1>Reports</h1>
        <p>Power BI reads reporting views populated by Python analytics.</p>
      </header>
      <section className="panel">
        {reportUrl ? <a className="button" href={reportUrl}>Open Power BI Report</a> : <p>Power BI report URL is not configured.</p>}
      </section>
    </div>
  );
}
