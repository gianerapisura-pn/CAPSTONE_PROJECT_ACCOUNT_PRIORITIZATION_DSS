import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "@/components/auth-provider";

function Harness(){const {user,demoSignIn,signOut}=useAuth();return <><span>{user?.displayName||"Signed out"}</span><button onClick={demoSignIn}>Demo login</button><button onClick={()=>signOut()}>Logout</button></>}

test("demo login persists for the current browser session and logout clears it",async()=>{
 const user=userEvent.setup();render(<AuthProvider><Harness/></AuthProvider>);
 expect(await screen.findByText("Signed out")).toBeInTheDocument();
 await user.click(screen.getByRole("button",{name:"Demo login"}));
 expect(screen.getByText("Demo Administrator")).toBeInTheDocument();
 expect(sessionStorage.getItem("peslc-demo-session")).toBe("administrator");
 await user.click(screen.getByRole("button",{name:"Logout"}));
 expect(screen.getByText("Signed out")).toBeInTheDocument();
});
