import { useTaskConfig, useUpdateTaskConfig } from "@/api/config";
import { TASK_TYPES } from "@/api/tasks";
import type { RawFileOrganizeConfig } from "@/api/types";
import { getErrorMessage } from "@/lib/errors";
import { useEffect, useState } from "react";
import {
  ConfigError,
  ConfigHeader,
  ConfigLoading,
  EnabledCheckbox,
  SubmitState,
  getMutationError,
  getPathError,
} from "./ConfigFormPrimitives";
import MediaPickerDialog from "./MediaPickerDialog";
import PathInput from "./PathInput";

interface ConfigPanelProps {
  rootPath: string | null;
}

interface RawFormState {
  enabled: boolean;
  workspaceRoot: string;
}

const emptyRawForm: RawFormState = {
  enabled: false,
  workspaceRoot: "",
};

function toRawForm(
  config: RawFileOrganizeConfig,
  enabled: boolean,
): RawFormState {
  return {
    enabled,
    workspaceRoot: config.workspace_root,
  };
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
