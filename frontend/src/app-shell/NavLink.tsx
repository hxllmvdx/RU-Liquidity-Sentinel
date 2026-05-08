"use client";

import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/shared/lib/cn";

export function NavLink({
  href,
  icon: Icon,
  children
}: {
  href: string;
  icon: LucideIcon;
  children: string;
}) {
  const pathname = usePathname();
  const active = pathname === href || pathname.startsWith(`${href}/`);

  return (
    <Link
      className={cn(
        "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
        active ? "bg-primary text-white shadow-panel" : "text-muted hover:bg-primary-soft hover:text-primary"
      )}
      href={href}
    >
      <Icon className="h-4 w-4" />
      <span>{children}</span>
    </Link>
  );
}
