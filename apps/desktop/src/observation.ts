import type { WindowSnapshot } from "./contracts.generated";

/** Local text is display data. Never feed it to prompts, links or actions here. */
export function acceptSnapshot(
  value: WindowSnapshot,
  taskId: string,
): WindowSnapshot {
  if (
    value.schema_version !== "1.0" ||
    value.kind !== "untrusted_ui_data" ||
    value.task_id !== taskId ||
    value.cloud_allowed !== false ||
    value.input_actions !== 0 ||
    value.screenshots !== 0 ||
    !Array.isArray(value.nodes) ||
    value.nodes.length > 64 ||
    value.nodes.some(
      (node, index) =>
        node.id !== index ||
        typeof node.text !== "string" ||
        node.text.length > 2000 ||
        (node.protected &&
          !["[protected]", "[unavailable]"].includes(node.text)),
    )
  )
    throw new Error("Invalid local window result.");
  return value;
}

export function observedText(snapshot: WindowSnapshot): string {
  return snapshot.nodes
    .filter((node) => !node.protected && node.text.trim())
    .map((node) => node.text)
    .join("\n\n");
}
