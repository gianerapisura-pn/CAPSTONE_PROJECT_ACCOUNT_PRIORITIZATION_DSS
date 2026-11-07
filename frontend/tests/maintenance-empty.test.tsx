import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { AliasReviewPanel } from "@/components/alias-review-panel";
import { CollectionCorrectionPanel } from "@/components/collection-correction-panel";
const state=vi.hoisted(()=>({aliases:[] as {alias_review_id:string;candidate_name:string;possible_canonical_name:string;status:string;reason:null}[]}));
vi.mock("@/lib/use-api",()=>({useApi:(path:string)=>({data:path.startsWith("/account-aliases")?state.aliases:[],loading:false,error:"",reload:vi.fn()})}));
vi.mock("@/lib/api",()=>({apiFetch:vi.fn()}));

test("empty maintenance queues do not render oversized alias or correction panels",()=>{
 render(<><AliasReviewPanel/><CollectionCorrectionPanel/></>);
 expect(screen.queryByRole("heading",{name:/alias review/i})).not.toBeInTheDocument();
 expect(screen.queryByRole("heading",{name:/collection correction review/i})).not.toBeInTheDocument();
 expect(screen.queryByRole("table")).not.toBeInTheDocument();
 expect(screen.getByText("Collection correction history").tagName).toBe("SUMMARY");
});

test("a real alias review remains visible without automatically merging identities",()=>{
 state.aliases=[{alias_review_id:"a1",candidate_name:"Recorded alternate",possible_canonical_name:"Verified account",status:"pending",reason:null}];
 try{render(<AliasReviewPanel/>);expect(screen.getByRole("heading",{name:/Account alias review/})).toBeInTheDocument();expect(screen.getByText("Recorded alternate")).toBeInTheDocument();expect(screen.getByRole("button",{name:"Approve alias"})).toBeEnabled();expect(screen.getByText(/not applied by ETL/)).toBeInTheDocument();}finally{state.aliases=[];}
});
