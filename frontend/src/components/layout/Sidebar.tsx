const items = ["dashboard", "modules", "forecast", "scenario", "backtest", "analyst"];

export function Sidebar() {
  return (
    <aside className="border-r border-slate-200 bg-white p-6">
      <div className="mb-8 text-lg font-semibold">RU Liquidity Sentinel</div>
      <nav className="space-y-2">
        {items.map((item) => (
          <a key={item} className="block rounded-xl px-3 py-2 hover:bg-slate-100" href={`/${item}`}>
            {item}
          </a>
        ))}
      </nav>
    </aside>
  );
}
