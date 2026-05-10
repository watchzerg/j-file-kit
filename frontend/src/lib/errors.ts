import { ApiResponseError } from "@/api/client";

const ERROR_MESSAGES: Record<string, string> = {
  TASK_ALREADY_RUNNING: "任务已在运行中，请等待当前任务完成",
  TASK_NOT_FOUND: "任务不存在",
  TASK_NOT_TERMINAL: "只能删除已结束的任务",
  RUN_NOT_FOUND: "执行实例不存在",
  INVALID_CONFIG: "配置无效，请检查配置参数",
  CONFIG_NOT_FOUND: "任务配置不存在",
  INVALID_PATH: "路径无效，请选择媒体目录下的文件夹",
  PERMISSION_DENIED: "没有权限访问该路径",
  UNKNOWN: "发生未知错误，请稍后重试",
};

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiResponseError) {
    return ERROR_MESSAGES[error.code] ?? error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return ERROR_MESSAGES.UNKNOWN;
}
