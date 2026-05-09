import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { ListDirectoriesResponse } from "./types";

export function useMediaDirectories(path: string) {
  return useQuery({
    queryKey: ["media", "directories", path],
    queryFn: () =>
      apiClient.get<ListDirectoriesResponse>(
        `/api/media/directories?path=${encodeURIComponent(path)}`,
      ),
  });
}
