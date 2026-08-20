import { ProtectedShell } from "@/components/protected-shell";

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) { return <ProtectedShell>{children}</ProtectedShell> }
