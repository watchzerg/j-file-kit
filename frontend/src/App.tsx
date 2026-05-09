import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppShell from "./components/layout/AppShell.tsx";
import ConfigPage from "./pages/ConfigPage.tsx";
import DashboardPage from "./pages/DashboardPage.tsx";
import MediaPage from "./pages/MediaPage.tsx";
import TaskDetailPage from "./pages/TaskDetailPage.tsx";
import TasksListPage from "./pages/TasksListPage.tsx";

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: 1,
      },
    },
  });
}

export default function App() {
  const [queryClient] = useState(createQueryClient);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/tasks" element={<TasksListPage />} />
            <Route path="/tasks/:runId" element={<TaskDetailPage />} />
            <Route path="/config" element={<ConfigPage />} />
            <Route path="/media" element={<MediaPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
