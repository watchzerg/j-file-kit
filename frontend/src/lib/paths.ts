export function isPathWithinRoot(path: string, root: string) {
  const normalizedPath = normalizePath(path);
  const normalizedRoot = normalizePath(root);
  return (
    normalizedPath === normalizedRoot ||
    normalizedPath.startsWith(`${normalizedRoot}/`)
  );
}

function normalizePath(path: string) {
  const trimmed = path.trim();
  if (trimmed === "/") {
    return "/";
  }
  return trimmed.replace(/\/+$/, "");
}
