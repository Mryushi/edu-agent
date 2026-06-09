import { Message } from "@langchain/langgraph-sdk";
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
// TODO  MS80OmFIVnBZMlhsc3JQbGxydm5uN002TmxOeFRRPT06ZTBiYjVlMDk=

export function extractStringFromMessageContent(message: Message): string {
  return typeof message.content === "string"
    ? message.content
    : Array.isArray(message.content)
    ? message.content
        .filter(
          (c: unknown) =>
            (typeof c === "object" &&
              c !== null &&
              "type" in c &&
              (c as { type: string }).type === "text") ||
            typeof c === "string"
        )
        .map((c: unknown) =>
          typeof c === "string"
            ? c
            : typeof c === "object" && c !== null && "text" in c
            ? (c as { text?: string }).text || ""
            : ""
        )
        .join("")
    : "";
}

export function extractSubAgentContent(data: unknown): string {
  if (typeof data === "string") {
    return data;
  }

  if (data && typeof data === "object") {
    const dataObj = data as Record<string, unknown>;

    // Try to extract description first
    if (dataObj.description && typeof dataObj.description === "string") {
      return dataObj.description;
    }

    // Then try prompt
    if (dataObj.prompt && typeof dataObj.prompt === "string") {
      return dataObj.prompt;
    }

    // For output objects, try result
    if (dataObj.result && typeof dataObj.result === "string") {
      return dataObj.result;
    }

    // Fallback to JSON stringification
    return JSON.stringify(data, null, 2);
  }

  // Fallback for any other type
  return JSON.stringify(data, null, 2);
}

export function isPreparingToCallTaskTool(messages: Message[]): boolean {
  const lastMessage = messages[messages.length - 1];
  return (
    (lastMessage.type === "ai" &&
      lastMessage.tool_calls?.some(
        (call: { name?: string }) => call.name === "task"
      )) ||
    false
  );
}

export function formatMessageForLLM(message: Message): string {
  let role: string;
  if (message.type === "human") {
    role = "Human";
  } else if (message.type === "ai") {
    role = "Assistant";
  } else if (message.type === "tool") {
    role = `Tool Result`;
  } else {
    role = message.type || "Unknown";
  }

  const timestamp = message.id ? ` (${message.id.slice(0, 8)})` : "";

  let contentText = "";

  // Extract content text
  if (typeof message.content === "string") {
    contentText = message.content;
  } else if (Array.isArray(message.content)) {
    const textParts: string[] = [];

    message.content.forEach((part: any) => {
      if (typeof part === "string") {
        textParts.push(part);
      } else if (part && typeof part === "object" && part.type === "text") {
        textParts.push(part.text || "");
      }
      // Ignore other types like tool_use in content - we handle tool calls separately
    });

    contentText = textParts.join("\n\n").trim();
  }

  // For tool messages, include additional tool metadata
  if (message.type === "tool") {
    const toolName = (message as any).name || "unknown_tool";
    const toolCallId = (message as any).tool_call_id || "";
    role = `Tool Result [${toolName}]`;
    if (toolCallId) {
      role += ` (call_id: ${toolCallId.slice(0, 8)})`;
    }
  }

  // Handle tool calls from .tool_calls property (for AI messages)
  const toolCallsText: string[] = [];
  if (
    message.type === "ai" &&
    message.tool_calls &&
    Array.isArray(message.tool_calls) &&
    message.tool_calls.length > 0
  ) {
    message.tool_calls.forEach((call: any) => {
      const toolName = call.name || "unknown_tool";
      const toolArgs = call.args ? JSON.stringify(call.args, null, 2) : "{}";
      toolCallsText.push(`[Tool Call: ${toolName}]\nArguments: ${toolArgs}`);
    });
  }

  // Combine content and tool calls
  const parts: string[] = [];
  if (contentText) {
    parts.push(contentText);
  }
  if (toolCallsText.length > 0) {
    parts.push(...toolCallsText);
  }

  if (parts.length === 0) {
    return `${role}${timestamp}: [Empty message]`;
  }

  if (parts.length === 1) {
    return `${role}${timestamp}: ${parts[0]}`;
  }

  return `${role}${timestamp}:\n${parts.join("\n\n")}`;
}

export function formatConversationForLLM(messages: Message[]): string {
  const formattedMessages = messages.map(formatMessageForLLM);
  return formattedMessages.join("\n\n---\n\n");
}

// Common image file extensions
const IMAGE_EXTS = new Set([
  "png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "ico", "tiff", "tif", "avif",
]);

function isImageUrl(url: string): boolean {
  try {
    const pathname = new URL(url).pathname.toLowerCase();
    const ext = pathname.split(".").pop() || "";
    if (IMAGE_EXTS.has(ext)) return true;
    // Some CDNs don't use file extensions; check common path segments
    const imagePatterns = [
      "/image/", "/img/", "/photo/", "/pic/", "/figure/",
      "/drawing/", "/chart/", "/diagram/", "/graph/", "/illustration/",
      "/capture/", "/screenshot/", "/afts/img/",
    ];
    return imagePatterns.some((p) => pathname.includes(p));
  } catch {
    return false;
  }
}

/**
 * Detects bare image URLs in text and wraps them in markdown image syntax
 * so they can be rendered as inline images.
 *
 * Skips URLs already wrapped in `![...](...)` or `[...](...)` markdown syntax.
 */
export function processImageUrlsInText(text: string): string {
  // Match URLs that are NOT already inside markdown link syntax `...](url)`
  // Strategy: split on markdown link patterns, process only the non-link parts
  const urlRe = /(https?:\/\/[^\s<>)]+)/g;
  return text.replace(urlRe, (url, offset) => {
    if (!isImageUrl(url)) return url;
    // Check if this URL is preceded by `](` (already a markdown link/image)
    const prefix = text.slice(Math.max(0, offset - 2), offset);
    if (prefix === "](") return url;
    return `![image](${url})`;
  });
}
// FIXME  My80OmFIVnBZMlhsc3JQbGxydm5uN002TmxOeFRRPT06ZTBiYjVlMDk=
