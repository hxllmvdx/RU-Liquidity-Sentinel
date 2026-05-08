import type { ReactNode } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-sand text-ink">
      <div className="mx-auto grid min-h-screen max-w-7xl grid-cols-1 md:grid-cols-[260px_1fr]">
        <Sidebar />
        <main className="p-4 md:p-8">
          <Header />
          <div className="mt-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
