import { useTaskConfig, useUpdateTaskConfig } from "@/api/config";
import { TASK_TYPES } from "@/api/tasks";
import type { JavVideoOrganizeConfig } from "@/api/types";
import { getErrorMessage } from "@/lib/errors";
import { useEffect, useState } from "react";
import {
  ConfigError,
  ConfigHeader,
  ConfigLoading,
  EnabledCheckbox,
  NumberInput,
  SubmitState,
  getMutationError,
  getPathError,
} from "./ConfigFormPrimitives";
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

interface ParsedJavNumbers {
  miscMaxSize: number;
  videoSmallDeleteBytes: number | null;
  inboxMaxSizeBytes: number;
  error: string | null;
}

const emptyJavForm: JavFormState = {
  enabled: false,
  workspaceRoot: "",
  miscMaxSize: "",
  videoSmallDeleteBytes: "",
  inboxExactStems: "",
  inboxMaxSizeBytes: "",
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

function splitTags(value: string) {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
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
