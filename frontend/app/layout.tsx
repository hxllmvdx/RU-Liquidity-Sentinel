import "@/styles/globals.css";
import { AppShell } from "@/app-shell/AppShell";
import { QueryProvider } from "@/app-shell/QueryProvider";
import type { ReactNode } from "react";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body>
        <QueryProvider>
          <AppShell>{children}</AppShell>
        </QueryProvider>
      </body>
    </html>
  );
}
