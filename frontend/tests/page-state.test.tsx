import { render, screen } from "@testing-library/react";
import { PageState } from "@/components/page-state";

test.each([
 {props:{loading:true},text:"Loading current DSS data"},
 {props:{loading:false,error:"API unavailable"},text:"API unavailable"},
 {props:{loading:false,empty:true},text:"No successful analysis yet"},
])("renders $text state",({props,text})=>{render(<PageState {...props}>Content</PageState>);expect(screen.getByText(text)).toBeInTheDocument()});
