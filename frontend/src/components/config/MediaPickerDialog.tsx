import { useMediaDirectories } from "@/api/media";
import type { DirectoryItem } from "@/api/types";
import { getErrorMessage } from "@/lib/errors";
import { useEffect, useState } from "react";

interface MediaPickerDialogProps {
  open: boolean;
  title: string;
  rootPath: string;
  selectedPath: string;
  onSelect: (path: string) => void;
  onClose: () => void;
}

export default function MediaPickerDialog({
  open,
  title,
  rootPath,
  selectedPath,
  onSelect,
  onClose,
}: MediaPickerDialogProps) {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(
    () => new Set([rootPath]),
  );

  useEffect(() => {
    if (open) {
      setExpandedPaths(new Set([rootPath]));
    }
  }, [open, rootPath]);

  if (!open) {
    return null;
  }

  function toggle(path: string) {
    setExpandedPaths((current) => {
      const next = new Set(current);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }

  function selectPath(path: string) {
    onSelect(path);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <dialog
        open
        aria-labelledby="media-picker-title"
        className="max-h-[80vh] w-full max-w-2xl overflow-hidden rounded-lg border bg-background shadow-lg"
      >
        <header className="flex items-center justify-between gap-4 border-b p-4">
          <div>
            <h2 id="media-picker-title" className="font-semibold text-lg">
              {title}
            </h2>
            <p className="mt-1 break-all text-muted-foreground text-sm">
              根目录：{rootPath}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border px-3 py-1.5 text-sm transition-colors hover:bg-muted"
          >
            关闭
          </button>
        </header>

        <div className="max-h-[60vh] overflow-auto p-4">
          <DirectoryNode
            path={rootPath}
            label={rootPath}
            selectedPath={selectedPath}
            expandedPaths={expandedPaths}
            onToggle={toggle}
            onSelect={selectPath}
          />
        </div>
      </dialog>
    </div>
  );
}

interface DirectoryNodeProps {
  path: string;
  label: string;
  selectedPath: string;
  expandedPaths: Set<string>;
  onToggle: (path: string) => void;
  onSelect: (path: string) => void;
}

function DirectoryNode({
  path,
  label,
  selectedPath,
  expandedPaths,
  onToggle,
  onSelect,
}: DirectoryNodeProps) {
  const isExpanded = expandedPaths.has(path);
  const directoriesQuery = useMediaDirectories(path, isExpanded);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2 rounded-md border p-2">
        <button
          type="button"
          onClick={() => onToggle(path)}
          className="rounded border px-2 py-1 text-xs transition-colors hover:bg-muted"
          aria-label={`${isExpanded ? "收起" : "展开"} ${path}`}
        >
          {isExpanded ? "收起" : "展开"}
        </button>
        <span
          className={
            selectedPath === path
              ? "break-all font-medium text-foreground text-sm"
              : "break-all text-sm"
          }
        >
          {label}
        </span>
        <button
          type="button"
          onClick={() => onSelect(path)}
          className="ml-auto rounded-md bg-foreground px-3 py-1.5 font-medium text-background text-xs transition-colors hover:bg-foreground/90"
        >
          选择
        </button>
      </div>

      {isExpanded ? (
        <div className="ml-4 border-l pl-3">
          {directoriesQuery.isLoading ? (
            <p className="py-2 text-muted-foreground text-sm">
              正在加载目录...
            </p>
          ) : null}
          {directoriesQuery.isError ? (
            <p className="py-2 text-red-600 text-sm">
              {getErrorMessage(directoriesQuery.error)}
            </p>
          ) : null}
          {directoriesQuery.data?.children.length === 0 ? (
            <p className="py-2 text-muted-foreground text-sm">没有子目录</p>
          ) : null}
          <div className="space-y-2">
            {directoriesQuery.data?.children.map((directory) => (
              <DirectoryChild
                key={directory.path}
                directory={directory}
                selectedPath={selectedPath}
                expandedPaths={expandedPaths}
                onToggle={onToggle}
                onSelect={onSelect}
              />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

interface DirectoryChildProps {
  directory: DirectoryItem;
  selectedPath: string;
  expandedPaths: Set<string>;
  onToggle: (path: string) => void;
  onSelect: (path: string) => void;
}

function DirectoryChild({
  directory,
  selectedPath,
  expandedPaths,
  onToggle,
  onSelect,
}: DirectoryChildProps) {
  return (
    <DirectoryNode
      path={directory.path}
      label={directory.name}
      selectedPath={selectedPath}
      expandedPaths={expandedPaths}
      onToggle={onToggle}
      onSelect={onSelect}
    />
  );
}
