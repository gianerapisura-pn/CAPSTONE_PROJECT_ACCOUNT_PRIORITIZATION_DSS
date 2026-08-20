import { AccountPriorityTable } from "@/components/account-priority-table";
import { demoPriorities } from "@/lib/demo-data";

export default function DashboardPage() {
  return (
    <div className="grid">
      <header>
        <h1>Account Prioritization</h1>
        <p>The DSS supports management in deciding which historical accounts should receive attention first.</p>
      </header>
      <section className="metrics">
        <div className="metric"><span>Latest Successful Run</span><strong>Demo</strong></div>
        <div className="metric"><span>Prioritized Accounts</span><strong>{demoPriorities.length}</strong></div>
        <div className="metric"><span>Analysis Cutoff</span><strong>Dynamic</strong></div>
        <div className="metric"><span>Power BI</span><strong>Setup</strong></div>
      </section>
      <AccountPriorityTable rows={demoPriorities} />
    </div>
  );
}
