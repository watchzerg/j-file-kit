import type { GetFileTaskConfigResponse } from "@/api/types";

export function getWorkspaceRoot(
  config: GetFileTaskConfigResponse | undefined,
) {
  const workspaceRoot = config?.config.workspace_root;
  return typeof workspaceRoot === "string" ? workspaceRoot : null;
}
