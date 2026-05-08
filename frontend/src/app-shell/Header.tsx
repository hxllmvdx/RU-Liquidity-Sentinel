import { Bell, Landmark, ShieldAlert } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-4 py-4 lg:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary text-white shadow-panel">
            <Landmark className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">RU Liquidity Sentinel</p>
            <h1 className="text-lg font-semibold">Liquidity stress early warning console</h1>
          </div>
        </div>
        <div className="flex items-center gap-3 text-sm text-muted">
          <div className="hidden items-center gap-2 rounded-full border bg-primary-soft px-3 py-1.5 md:flex">
            <ShieldAlert className="h-4 w-4 text-accent" />
            <span>Analytical monitoring mode</span>
          </div>
          <button className="rounded-full border bg-white p-2 text-primary transition hover:bg-primary-soft" type="button">
            <Bell className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
