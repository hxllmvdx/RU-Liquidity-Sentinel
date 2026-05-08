"use client";

import { Blocks, FlaskConical, LayoutDashboard, LineChart, MessageSquareText, Radar } from "lucide-react";
import { NavLink } from "@/app-shell/NavLink";
import { ROUTES } from "@/shared/config/routes";

const items = [
  { href: ROUTES.dashboard, label: "Дашборд", icon: LayoutDashboard },
  { href: ROUTES.modules, label: "Модули", icon: Blocks },
  { href: ROUTES.forecast, label: "Прогноз", icon: LineChart },
  { href: ROUTES.scenario, label: "Сценарий", icon: FlaskConical },
  { href: ROUTES.backtest, label: "Бэктест", icon: Radar },
  { href: ROUTES.analyst, label: "Аналитик", icon: MessageSquareText }
];

export function Sidebar() {
  return (
    <aside className="sticky top-24 hidden h-fit w-64 rounded-2xl border bg-white p-3 shadow-panel lg:block">
      <p className="px-3 pb-3 text-xs font-semibold uppercase tracking-[0.2em] text-muted">Навигация</p>
      <nav className="space-y-1">
        {items.map((item) => (
          <NavLink key={item.href} href={item.href} icon={item.icon}>
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
