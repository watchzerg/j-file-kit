import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";
import type {
  SystemFileTypeDefaultsResponse,
  SystemInfoResponse,
} from "./types";

export function useSystemInfo() {
  return useQuery({
    queryKey: ["system", "info"],
    queryFn: () => apiClient.get<SystemInfoResponse>("/api/system/info"),
    staleTime: Number.POSITIVE_INFINITY,
  });
}

export function useSystemFileTypeDefaults() {
  return useQuery({
    queryKey: ["system", "file-type-defaults"],
    queryFn: () =>
      apiClient.get<SystemFileTypeDefaultsResponse>(
        "/api/system/file-type-defaults",
      ),
    staleTime: Number.POSITIVE_INFINITY,
  });
}
