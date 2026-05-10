import { useTaskConfig, useUpdateTaskConfig } from "@/api/config";
import { TASK_TYPES } from "@/api/tasks";
import type {
  JavVideoOrganizeConfig,
  RawFileOrganizeConfig,
} from "@/api/types";
import { getErrorMessage } from "@/lib/errors";
import { isPathWithinRoot } from "@/lib/paths";
import { useEffect, useState } from "react";
import MediaPickerDialog from "./MediaPickerDialog";
import PathInput from "./PathInput";
import StemTagsInput from "./StemTagsInput";

interface ConfigPanelProps {
  rootPath: string | null;
}

interface JavFormState {
  enabled: boolean;
  workspaceRoot: string;
  miscMaxSize: string;
  videoSmallDeleteBytes: string;
  inboxExactStems: string;
  inboxMaxSizeBytes: string;
}

interface RawFormState {
  enabled: boolean;
  workspaceRoot: string;
}

export function JavConfigPanel({ rootPath }: ConfigPanelProps) {
  const configQuery = useTaskConfig(TASK_TYPES.JAV);
  const updateConfig = useUpdateTaskConfig(TASK_TYPES.JAV);
  const [form, setForm] = useState<JavFormState>(emptyJavForm);
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    if (configQuery.data) {
      setForm(toJavForm(configQuery.data.config, configQuery.data.enabled));
      setFormError(null);
    }
  }, [configQuery.data]);

  const pathError = getPathError(form.workspaceRoot, rootPath);

  function updateField(field: keyof JavFormState, value: string | boolean) {
    setForm((current) => ({ ...current, [field]: value }));
    setSuccessMessage(null);
    setFormError(null);
  }

  function submitForm(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pathError) {
      setFormError(pathError);
      return;
    }

    const parsedNumbers = parseJavNumbers(form);
    if (parsedNumbers.error) {
      setFormError(parsedNumbers.error);
      return;
    }

    updateConfig.mutate(
      {
        enabled: form.enabled,
        config: {
          workspace_root: form.workspaceRoot.trim(),
          misc_file_delete_rules: {
            max_size: parsedNumbers.miscMaxSize,
          },
          video_small_delete_bytes: parsedNumbers.videoSmallDeleteBytes,
          inbox_delete_rules: {
            exact_stems: splitTags(form.inboxExactStems),
            max_size_bytes: parsedNumbers.inboxMaxSizeBytes,
          },
        },
      },
      {
        onSuccess: () => {
          setSuccessMessage("JAV 视频整理配置已保存");
          setFormError(null);
        },
      },
    );
  }

  if (configQuery.isLoading) {
    return <ConfigLoading />;
  }
  if (configQuery.isError) {
    return <ConfigError message={getErrorMessage(configQuery.error)} />;
  }

  return (
    <section className="rounded-lg border bg-card p-5 shadow-sm">
      <ConfigHeader
        title="JAV 视频整理"
        description="配置 JAV 工作区、启用状态和可调删除策略。"
      />
      <form className="mt-6 space-y-5" onSubmit={submitForm}>
        <EnabledCheckbox
          checked={form.enabled}
          onChange={(checked) => updateField("enabled", checked)}
        />
        <PathInput
          id="jav-workspace-root"
          label="工作区"
          value={form.workspaceRoot}
          onChange={(value) => updateField("workspaceRoot", value)}
          onPick={() => setIsPickerOpen(true)}
          helperText={rootPath ? `必须位于 ${rootPath} 下` : undefined}
          error={pathError}
        />
        <div className="grid gap-4 md:grid-cols-2">
          <NumberInput
            id="jav-misc-max-size"
            label="Misc 删除最大体积（字节）"
            value={form.miscMaxSize}
            onChange={(value) => updateField("miscMaxSize", value)}
          />
          <NumberInput
            id="jav-video-small-delete-bytes"
            label="视频小文件删除阈值（字节，可空）"
            value={form.videoSmallDeleteBytes}
            onChange={(value) => updateField("videoSmallDeleteBytes", value)}
          />
          <NumberInput
            id="jav-inbox-max-size"
            label="收件箱预删除体积上限（字节）"
            value={form.inboxMaxSizeBytes}
            onChange={(value) => updateField("inboxMaxSizeBytes", value)}
          />
        </div>
        <StemTagsInput
          id="jav-inbox-exact-stems"
          label="收件箱预删除 exact stems"
          value={form.inboxExactStems}
          onChange={(value) => updateField("inboxExactStems", value)}
        />
        <SubmitState
          isPending={updateConfig.isPending}
          error={formError ?? getMutationError(updateConfig.error)}
          success={successMessage}
        />
      </form>
      {rootPath ? (
        <MediaPickerDialog
          open={isPickerOpen}
          title="选择 JAV 工作区"
          rootPath={rootPath}
          selectedPath={form.workspaceRoot}
          onSelect={(path) => updateField("workspaceRoot", path)}
          onClose={() => setIsPickerOpen(false)}
        />
      ) : null}
    </section>
  );
}

export function RawConfigPanel({ rootPath }: ConfigPanelProps) {
  const configQuery = useTaskConfig(TASK_TYPES.RAW);
  const updateConfig = useUpdateTaskConfig(TASK_TYPES.RAW);
  const [form, setForm] = useState<RawFormState>(emptyRawForm);
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    if (configQuery.data) {
      setForm(toRawForm(configQuery.data.config, configQuery.data.enabled));
      setFormError(null);
    }
  }, [configQuery.data]);

  const pathError = getPathError(form.workspaceRoot, rootPath);

  function updateField(field: keyof RawFormState, value: string | boolean) {
    setForm((current) => ({ ...current, [field]: value }));
    setSuccessMessage(null);
    setFormError(null);
  }

  function submitForm(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pathError) {
      setFormError(pathError);
      return;
    }

    updateConfig.mutate(
      {
        enabled: form.enabled,
        config: {
          workspace_root: form.workspaceRoot.trim(),
        },
      },
      {
        onSuccess: () => {
          setSuccessMessage("Raw 文件整理配置已保存");
          setFormError(null);
        },
      },
    );
  }

  if (configQuery.isLoading) {
    return <ConfigLoading />;
  }
  if (configQuery.isError) {
    return <ConfigError message={getErrorMessage(configQuery.error)} />;
  }

  return (
    <section className="rounded-lg border bg-card p-5 shadow-sm">
      <ConfigHeader
        title="Raw 文件整理"
        description="当前 Raw 配置只开放工作区与启用状态。"
      />
      <form className="mt-6 space-y-5" onSubmit={submitForm}>
        <EnabledCheckbox
          checked={form.enabled}
          onChange={(checked) => updateField("enabled", checked)}
        />
        <PathInput
          id="raw-workspace-root"
          label="工作区"
          value={form.workspaceRoot}
          onChange={(value) => updateField("workspaceRoot", value)}
          onPick={() => setIsPickerOpen(true)}
          helperText={rootPath ? `必须位于 ${rootPath} 下` : undefined}
          error={pathError}
        />
        <SubmitState
          isPending={updateConfig.isPending}
          error={formError ?? getMutationError(updateConfig.error)}
          success={successMessage}
        />
      </form>
      {rootPath ? (
        <MediaPickerDialog
          open={isPickerOpen}
          title="选择 Raw 工作区"
          rootPath={rootPath}
          selectedPath={form.workspaceRoot}
          onSelect={(path) => updateField("workspaceRoot", path)}
          onClose={() => setIsPickerOpen(false)}
        />
      ) : null}
    </section>
  );
}

function ConfigHeader({
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

function EnabledCheckbox({
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

function NumberInput({
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

function SubmitState({
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

function ConfigLoading() {
  return (
    <section className="rounded-lg border bg-card p-5 text-muted-foreground text-sm">
      正在加载配置...
    </section>
  );
}

function ConfigError({ message }: { message: string }) {
  return (
    <section className="rounded-lg border border-red-200 bg-red-50 p-5 text-red-700 text-sm">
      {message}
    </section>
  );
}

const emptyJavForm: JavFormState = {
  enabled: false,
  workspaceRoot: "",
  miscMaxSize: "",
  videoSmallDeleteBytes: "",
  inboxExactStems: "",
  inboxMaxSizeBytes: "",
};

const emptyRawForm: RawFormState = {
  enabled: false,
  workspaceRoot: "",
};

function toJavForm(
  config: JavVideoOrganizeConfig,
  enabled: boolean,
): JavFormState {
  return {
    enabled,
    workspaceRoot: config.workspace_root,
    miscMaxSize: String(config.misc_file_delete_rules.max_size ?? ""),
    videoSmallDeleteBytes:
      config.video_small_delete_bytes === null
        ? ""
        : String(config.video_small_delete_bytes),
    inboxExactStems: config.inbox_delete_rules.exact_stems.join(", "),
    inboxMaxSizeBytes: String(config.inbox_delete_rules.max_size_bytes),
  };
}

function toRawForm(
  config: RawFileOrganizeConfig,
  enabled: boolean,
): RawFormState {
  return {
    enabled,
    workspaceRoot: config.workspace_root,
  };
}

function getPathError(path: string, rootPath: string | null) {
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

function splitTags(value: string) {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

interface ParsedJavNumbers {
  miscMaxSize: number;
  videoSmallDeleteBytes: number | null;
  inboxMaxSizeBytes: number;
  error: string | null;
}

function parseJavNumbers(form: JavFormState): ParsedJavNumbers {
  const miscMaxSize = parseNonNegativeInteger(form.miscMaxSize);
  if (miscMaxSize === null) {
    return invalidNumbers("Misc 删除最大体积必须是非负整数");
  }

  const videoSmallDeleteBytes = form.videoSmallDeleteBytes.trim()
    ? parseNonNegativeInteger(form.videoSmallDeleteBytes)
    : null;
  if (form.videoSmallDeleteBytes.trim() && videoSmallDeleteBytes === null) {
    return invalidNumbers("视频小文件删除阈值必须是非负整数或留空");
  }

  const inboxMaxSizeBytes = parseNonNegativeInteger(form.inboxMaxSizeBytes);
  if (inboxMaxSizeBytes === null) {
    return invalidNumbers("收件箱预删除体积上限必须是非负整数");
  }

  return {
    miscMaxSize,
    videoSmallDeleteBytes,
    inboxMaxSizeBytes,
    error: null,
  };
}

function parseNonNegativeInteger(value: string) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 0) {
    return null;
  }
  return parsed;
}

function invalidNumbers(error: string): ParsedJavNumbers {
  return {
    miscMaxSize: 0,
    videoSmallDeleteBytes: null,
    inboxMaxSizeBytes: 0,
    error,
  };
}

function getMutationError(error: unknown) {
  return error ? getErrorMessage(error) : null;
}
