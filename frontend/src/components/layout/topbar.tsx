"use client";

import { usePathname } from "next/navigation";

import { ThemeToggle } from "@/components/theme-toggle";

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/jobs": "Jobs",
  "/applications": "Applications",
  "/resumes": "Resumes",
};

export function Topbar() {
  const pathname = usePathname();
  const title =
    TITLES[pathname] ??
    Object.entries(TITLES).find(([href]) => href !== "/" && pathname.startsWith(href))?.[1] ??
    "Job OS";

  return (
    <header className="flex h-14 items-center justify-between border-b px-6">
      <h1 className="font-heading text-base font-semibold">{title}</h1>
      <ThemeToggle />
    </header>
  );
}
