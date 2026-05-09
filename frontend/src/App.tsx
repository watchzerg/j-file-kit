import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import ConfigPage from "./pages/ConfigPage.tsx";
import MediaPage from "./pages/MediaPage.tsx";
import TasksPage from "./pages/TasksPage.tsx";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<TasksPage />} />
          <Route path="/config" element={<ConfigPage />} />
          <Route path="/media" element={<MediaPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
