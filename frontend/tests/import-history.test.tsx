import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ImportHistoryTable } from "@/components/import-history-table";
import { downloadExport } from "@/lib/api";
vi.mock("@/lib/api",()=>({downloadExport:vi.fn()}));
vi.mock("@/lib/use-api",()=>({useApi:()=>({loading:false,error:"",reload:vi.fn(),data:{issues:[{source_sheet:"CSV",row_number:2,column:"EWT",severity:"warning",message:"Missing EWT is not recorded zero."}]}})}));

test("import overview keeps statuses and exposes validation evidence only through selected batch details", async()=>{
  const rows=[{import_batch_id:"batch-current",file_name:"Current.csv",file_hash:"test-hash",uploaded_at:"2030-01-01",status:"committed",rows_discovered:4,rows_accepted:2,rows_flagged:2,rows_excluded:0,cancelled_count:0,analysis_run_id:"run-12345"},{import_batch_id:"batch-old",file_name:"Older.csv",file_hash:"old-hash",uploaded_at:"2029-01-01",status:"superseded",rows_discovered:3,rows_accepted:3,rows_flagged:0,rows_excluded:0,cancelled_count:0,analysis_run_id:null}];
  const before=JSON.stringify(rows);
  render(<ImportHistoryTable items={rows}/>);
  expect(screen.queryByRole("columnheader",{name:/Accepted|Flagged|Issues/i})).not.toBeInTheDocument();
  expect(screen.getByText("superseded")).toBeInTheDocument();
  expect(screen.queryByRole("button",{name:/Download validation/})).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button",{name:"View import details: Current.csv"}));
  const details=screen.getByRole("region",{name:"Import details: Current.csv"});
  expect(within(details).getByText(/Blank EWT remains different/)).toBeInTheDocument();
  expect(within(details).getByText(/Missing EWT is not recorded zero/)).toBeInTheDocument();
  await userEvent.click(within(details).getByRole("button",{name:"Download validation issue report"}));
  expect(downloadExport).toHaveBeenCalledWith("/imports/batch-current/issues.csv","import-batch-current-issues.csv");
  await userEvent.click(screen.getByRole("button",{name:"Close import details"}));
  expect(screen.queryByRole("region")).not.toBeInTheDocument();
  expect(JSON.stringify(rows)).toBe(before);
});
