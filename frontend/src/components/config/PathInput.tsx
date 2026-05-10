interface PathInputProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  onPick: () => void;
  helperText?: string;
  error?: string | null;
}

export default function PathInput({
  id,
  label,
  value,
  onChange,
  onPick,
  helperText,
  error,
}: PathInputProps) {
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="font-medium text-sm">
        {label}
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="min-w-0 flex-1 rounded-md border bg-background px-3 py-2 text-sm outline-none focus:border-foreground"
        />
        <button
          type="button"
          onClick={onPick}
          className="rounded-md border px-3 py-2 font-medium text-sm transition-colors hover:bg-muted"
        >
          选择目录
        </button>
      </div>
      {helperText ? (
        <p className="text-muted-foreground text-sm">{helperText}</p>
      ) : null}
      {error ? <p className="text-red-600 text-sm">{error}</p> : null}
    </div>
  );
}
