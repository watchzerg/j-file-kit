import { Layers } from "lucide-react";
import { NavLink } from "react-router-dom";

const navItems = [
  { label: "Dashboard", to: "/", end: true },
  { label: "任务列表", to: "/tasks", end: false },
  { label: "配置", to: "/config", end: false },
  { label: "媒体", to: "/media", end: false },
] as const;

export default function TopNav() {
  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur">
      <div className="container mx-auto flex h-14 items-center justify-between px-4">
        <NavLink
          to="/"
          className="flex items-center gap-2 font-semibold text-lg text-foreground"
        >
          <Layers className="h-5 w-5" aria-hidden="true" />
          <span>j-file-kit</span>
        </NavLink>

        <nav className="flex items-center gap-4" aria-label="主导航">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                [
                  "text-sm transition-colors",
                  isActive
                    ? "font-medium text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                ].join(" ")
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
