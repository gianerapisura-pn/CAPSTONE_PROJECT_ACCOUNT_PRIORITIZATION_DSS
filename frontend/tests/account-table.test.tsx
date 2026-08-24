import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AccountPriorityTable } from "@/components/account-priority-table";
import type { AccountPriority } from "@/types/dss";

const base={rfm_score:4,settlement_days_avg:20,normalized_recency:.8,normalized_frequency:.7,normalized_monetary:.6,normalized_settlement:.7,recency_contribution:.2,frequency_contribution:.2,monetary_contribution:.2,settlement_contribution:.2,latest_valid_transaction:"2030-01-01",recency_days:10,frequency:3,monetary:1000,recency_score:5,frequency_score:4,monetary_score:3};
const rows:AccountPriority[]=[
 {account:"ALPHA",priority_rank:1,priority_group:"High",final_priority_score:.9,inactivity_risk:"Lower",...base},
 {account:"BETA",priority_rank:2,priority_group:"Low",final_priority_score:.4,inactivity_risk:"Higher",...base},
];

test("search and priority filters operate on API-shaped account data",async()=>{
 const user=userEvent.setup();render(<AccountPriorityTable rows={rows}/>);
 expect(screen.getByText("ALPHA")).toBeInTheDocument();expect(screen.getByText("BETA")).toBeInTheDocument();
 await user.type(screen.getByLabelText("Search accounts"),"beta");
 expect(screen.queryByText("ALPHA")).not.toBeInTheDocument();expect(screen.getByText("BETA")).toBeInTheDocument();
 await user.clear(screen.getByLabelText("Search accounts"));
 await user.selectOptions(screen.getByLabelText("Priority Group"),"High");
 expect(screen.getByText("ALPHA")).toBeInTheDocument();expect(screen.queryByText("BETA")).not.toBeInTheDocument();
});

test("priority group and inactivity risk remain visibly separate columns",()=>{
 render(<AccountPriorityTable rows={rows}/>);
 expect(screen.getByRole("columnheader",{name:"Priority"})).toBeInTheDocument();
 expect(screen.getByRole("columnheader",{name:"Inactivity risk"})).toBeInTheDocument();
 expect(screen.getByRole("columnheader",{name:"Recency"})).toBeInTheDocument();
 expect(screen.queryByRole("columnheader",{name:"Normalized RFM"})).not.toBeInTheDocument();
});
