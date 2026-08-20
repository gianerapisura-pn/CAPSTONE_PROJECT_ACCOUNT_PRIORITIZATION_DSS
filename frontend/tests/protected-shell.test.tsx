import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const replace=vi.fn();
vi.mock("next/navigation",()=>({usePathname:()=>"/dashboard",useRouter:()=>({replace})}));
vi.mock("@/components/auth-provider",()=>({useAuth:()=>({
 user:{userId:"m1",email:"manager@example.test",role:"management",displayName:"Manager",demo:false},
 loading:false,signOut:vi.fn(),
})}));
import { ProtectedShell } from "@/components/protected-shell";

test("management navigation excludes administrator operations",()=>{
 render(<ProtectedShell><div>Dashboard API content</div></ProtectedShell>);
 expect(screen.getByText("Dashboard API content")).toBeInTheDocument();
 expect(screen.getByRole("link",{name:/Account Prioritization/})).toBeInTheDocument();
 expect(screen.queryByRole("link",{name:/Import Data/})).not.toBeInTheDocument();
 expect(screen.queryByRole("link",{name:/Analytics Runs/})).not.toBeInTheDocument();
});
