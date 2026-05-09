import { cn } from "@/lib/utils";

interface DryRunBadgeProps {
  className?: string;
}

export default function DryRunBadge({ className }: DryRunBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-orange-300 bg-orange-50 px-2 py-0.5 font-medium text-orange-700 text-xs",
        className,
      )}
    >
      Dry Run
    </span>
  );
}
