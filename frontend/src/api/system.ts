import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { SystemInfoResponse } from "./types";

export function useSystemInfo() {
  return useQuery({
    queryKey: ["system", "info"],
    queryFn: () => apiClient.get<SystemInfoResponse>("/api/system/info"),
    staleTime: Number.POSITIVE_INFINITY,
  });
}
