import { getErrorMessage } from "@/lib/errors";
import { isPathWithinRoot } from "@/lib/paths";

export function ConfigHeader({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div>
      <h2 className="font-semibold text-xl">{title}</h2>
      <p className="mt-1 text-muted-foreground text-sm">{description}</p>
    </div>
  );
}

export function EnabledCheckbox({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 rounded border"
      />
      启用任务
    </label>
  );
}

export function NumberInput({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="font-medium text-sm">
        {label}
      </label>
      <input
        id={id}
        type="number"
        min="0"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:border-foreground"
      />
    </div>
  );
}

export function SubmitState({
  isPending,
  error,
  success,
}: {
  isPending: boolean;
  error: string | null;
  success: string | null;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <button
        type="submit"
        disabled={isPending}
        className="rounded-md bg-foreground px-4 py-2 font-medium text-background text-sm transition-colors hover:bg-foreground/90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isPending ? "保存中..." : "保存配置"}
      </button>
      {error ? <p className="text-red-600 text-sm">{error}</p> : null}
      {success ? <p className="text-green-700 text-sm">{success}</p> : null}
    </div>
  );
}

export function ConfigLoading() {
  return (
    <section className="rounded-lg border bg-card p-5 text-muted-foreground text-sm">
      正在加载配置...
    </section>
  );
}

export function ConfigError({ message }: { message: string }) {
  return (
    <section className="rounded-lg border border-red-200 bg-red-50 p-5 text-red-700 text-sm">
      {message}
    </section>
  );
}

export function getPathError(path: string, rootPath: string | null) {
  if (!path.trim()) {
    return "工作区不能为空";
  }
  if (!rootPath) {
    return "系统根目录信息加载后才能保存";
  }
  if (!isPathWithinRoot(path, rootPath)) {
    return `工作区必须位于 ${rootPath} 下`;
  }
  return null;
}

export function getMutationError(error: unknown) {
  return error ? getErrorMessage(error) : null;
}
