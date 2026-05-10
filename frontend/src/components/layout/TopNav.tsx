import { useSystemInfo } from "@/api/system";
import { Layers } from "lucide-react";
import { NavLink } from "react-router-dom";

const navItems = [
  { label: "Dashboard", to: "/", end: true },
  { label: "任务列表", to: "/tasks", end: false },
  { label: "配置", to: "/config", end: false },
] as const;

export default function TopNav() {
  const systemInfoQuery = useSystemInfo();
  const appVersion = systemInfoQuery.data?.app_version;

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur">
      <div className="container mx-auto flex h-14 items-center justify-between gap-4 px-4">
        <NavLink
          to="/"
          className="flex min-w-0 items-center gap-2 font-semibold text-lg text-foreground"
        >
          <Layers className="h-5 w-5 shrink-0" aria-hidden="true" />
          <span className="truncate">j-file-kit</span>
        </NavLink>

        <div className="flex shrink-0 items-center gap-4">
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
          <span
            className="hidden text-muted-foreground text-xs sm:inline"
            title="应用版本"
          >
            {appVersion ?? "…"}
          </span>
        </div>
      </div>
    </header>
  );
}
