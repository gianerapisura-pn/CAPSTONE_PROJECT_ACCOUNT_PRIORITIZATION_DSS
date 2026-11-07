import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import ImportPage from "@/app/(protected)/import/page";
const state=vi.hoisted(()=>({role:"administrator",status:"pending"}));
vi.mock("@/components/auth-provider",()=>({useAuth:()=>({user:{role:state.role}})}));
vi.mock("@/lib/api",()=>({apiFetch:vi.fn(),downloadExport:vi.fn()}));
vi.mock("@/lib/use-api",()=>({useApi:()=>({data:state.status === "empty" ? [] : [{collection_correction_review_id:"review-1",status:state.status,candidates:[],selected_raw_source_row_id:null,reason:null}],error:"",loading:false,reload:vi.fn()})}));
test("administrator discovers pending corrections in the Data Import workflow",()=>{
 render(<ImportPage/>);
 expect(screen.getByText(/Collection records require review/)).toBeInTheDocument();
 expect(screen.getByRole("button",{name:"Review corrections"})).toBeInTheDocument();
 expect(screen.getByRole("button",{name:"Choose source file"})).toBeInTheDocument();
 expect(screen.queryByRole("heading",{name:"Collection correction review"})).not.toBeInTheDocument();
});
test("normal import has no correction panel or empty history control",()=>{
 state.status="empty";
 try {render(<ImportPage/>);expect(screen.getByRole("button",{name:"Choose source file"})).toBeInTheDocument();expect(screen.queryByText(/correction/i)).not.toBeInTheDocument();}finally{state.status="pending";}
});
test("management receives no import or correction controls",()=>{
 state.role="management";
 try {render(<ImportPage/>);expect(screen.queryByRole("button",{name:"Review corrections"})).not.toBeInTheDocument();expect(screen.queryByRole("button",{name:"Choose source file"})).not.toBeInTheDocument();}finally{state.role="administrator";}
});
