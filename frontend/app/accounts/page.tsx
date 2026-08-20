import { AccountPriorityTable } from "@/components/account-priority-table";
import { demoPriorities } from "@/lib/demo-data";

export default function AccountsPage() {
  return (
    <div className="grid">
      <header>
        <h1>Account Ranking</h1>
        <p>Priority Group indicates recommended order for management attention. Inactivity Risk is separate predictive context.</p>
      </header>
      <AccountPriorityTable rows={demoPriorities} />
    </div>
  );
}
