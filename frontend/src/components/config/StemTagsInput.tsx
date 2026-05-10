interface StemTagsInputProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
}

export default function StemTagsInput({
  id,
  label,
  value,
  onChange,
}: StemTagsInputProps) {
  const tags = value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);

  return (
    <div className="space-y-2">
      <label htmlFor={id} className="font-medium text-sm">
        {label}
      </label>
      <input
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="用英文逗号分隔，例如 sample, thumbs"
        className="w-full rounded-md border bg-background px-3 py-2 text-sm outline-none focus:border-foreground"
      />
      <div className="flex flex-wrap gap-2">
        {tags.length > 0 ? (
          tags.map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-muted px-2 py-1 text-muted-foreground text-xs"
            >
              {tag}
            </span>
          ))
        ) : (
          <span className="text-muted-foreground text-sm">
            当前没有匹配 stem
          </span>
        )}
      </div>
    </div>
  );
}
