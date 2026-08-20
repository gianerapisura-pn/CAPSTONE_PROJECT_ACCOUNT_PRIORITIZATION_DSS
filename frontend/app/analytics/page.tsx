export default function AnalyticsPage() {
  return (
    <div className="grid">
      <header>
        <h1>Analytics</h1>
        <p>Python computes descriptive, predictive, and prescriptive outputs before the UI and Power BI read them.</p>
      </header>
      <section className="metrics">
        <div className="metric"><span>Descriptive</span><strong>RFM</strong></div>
        <div className="metric"><span>Settlement</span><strong>Duration</strong></div>
        <div className="metric"><span>Predictive</span><strong>CART</strong></div>
        <div className="metric"><span>Prescriptive</span><strong>CRITIC/MCS</strong></div>
      </section>
      <section className="panel">
        <h2>Sensitivity</h2>
        <p>Configured ranges are +/-10, +/-20, +/-30, and +/-40 percent weight perturbations with Spearman and group movement outputs.</p>
      </section>
    </div>
  );
}
