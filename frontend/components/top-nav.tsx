"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function TopNav() {
  const pathname = usePathname();
  return (
    <nav className="tabs" aria-label="Primary">
      <Link className="tab" href="/" aria-current={pathname === "/" ? "page" : undefined}>
        <span className="tabBeta">beta</span>
        Debug
      </Link>
      <Link className="tab" href="/history" aria-current={pathname === "/history" ? "page" : undefined}>
        History
      </Link>
      <Link className="tab" href="/settings" aria-current={pathname === "/settings" ? "page" : undefined}>
        Settings
      </Link>
    </nav>
  );
}
