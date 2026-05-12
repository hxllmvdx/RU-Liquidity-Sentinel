import type { ReactNode } from "react";
import { Header } from "@/app-shell/Header";
import { Sidebar } from "@/app-shell/Sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <Header />
      <div className="mx-auto flex w-full max-w-[1600px] gap-6 px-4 pb-8 pt-6 lg:px-6">
        <Sidebar />
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
