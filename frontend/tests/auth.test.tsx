import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, vi } from "vitest";
import { AuthProvider, useAuth } from "@/components/auth-provider";

function Harness(){const {user,demo,demoSignIn,signOut}=useAuth();return <><span>{user?.displayName||"Signed out"}</span><span>{demo?"Demo mode":"Production mode"}</span><button onClick={demoSignIn}>Demo login</button><button onClick={()=>signOut()}>Logout</button></>}

afterEach(() => vi.unstubAllEnvs());

test("demo login persists for the current browser session and logout clears it",async()=>{
 vi.stubEnv("NEXT_PUBLIC_DEMO_MODE","true");
 const user=userEvent.setup();render(<AuthProvider><Harness/></AuthProvider>);
 expect(await screen.findByText("Signed out")).toBeInTheDocument();
 expect(screen.getByText("Demo mode")).toBeInTheDocument();
 await user.click(screen.getByRole("button",{name:"Demo login"}));
 expect(screen.getByText("Demo Administrator")).toBeInTheDocument();
 expect(sessionStorage.getItem("peslc-demo-session")).toBe("administrator");
 await user.click(screen.getByRole("button",{name:"Logout"}));
 expect(screen.getByText("Signed out")).toBeInTheDocument();
});

test("missing production Supabase configuration does not silently enable demo mode",async()=>{
 vi.stubEnv("NEXT_PUBLIC_DEMO_MODE","false");
 vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL","");
 vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY","");
 render(<AuthProvider><Harness/></AuthProvider>);
 expect(await screen.findByText("Signed out")).toBeInTheDocument();
 expect(screen.getByText("Production mode")).toBeInTheDocument();
});
