import { Outlet } from "react-router-dom";
import GlobalRunBanner from "./GlobalRunBanner.tsx";
import TopNav from "./TopNav.tsx";

export default function AppShell() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <TopNav />
      <GlobalRunBanner />
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}
