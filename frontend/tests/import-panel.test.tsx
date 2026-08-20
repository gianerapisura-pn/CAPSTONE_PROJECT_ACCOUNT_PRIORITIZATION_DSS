import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ImportPanel } from "@/components/import-panel";

vi.mock("@/lib/api",()=>({downloadExport:vi.fn(),apiFetch:vi.fn().mockResolvedValue({import_batch_id:"b1",file_name:"bad.csv",file_hash:"abc",sheets:["CSV"],rows_discovered:1,cancelled_count:0,can_commit:false,duplicate_committed_file:false,status:"PREVIEW",issues:[{row_number:2,column:"SI DATE",severity:"error",message:"Invalid SI date."}]})}));

test("invalid preview clearly remains uncommittable",async()=>{
 const user=userEvent.setup();render(<ImportPanel/>);
 const file=new File(["bad"],"bad.csv",{type:"text/csv"});
 const hidden=document.querySelector('input[type="file"]') as HTMLInputElement;
 await user.upload(hidden,file);await user.click(screen.getByRole("button",{name:/Validate and preview/i}));
 expect(await screen.findByText("Invalid SI date.")).toBeInTheDocument();
 expect(screen.getByRole("button",{name:"Confirm import"})).toBeDisabled();
});
