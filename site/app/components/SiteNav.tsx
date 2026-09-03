"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Resultados" },
  { href: "/methodology", label: "Metodología" },
  { href: "/axolotl", label: "Axolotl" },
];

export function SiteNav() {
  const pathname = usePathname();
  return (
    <nav className="site-nav">
      <div className="container site-nav-inner">
        <Link href="/" className="site-brand">
          Tamiz
        </Link>
        <div className="site-nav-links">
          {LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`nav-link${pathname === href ? " active" : ""}`}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
