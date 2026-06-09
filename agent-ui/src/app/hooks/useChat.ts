"use client";
// FIXME  MC80OmFIVnBZMlhsc3JQbGxydm5uN002UkRSYVZRPT06NTQ4NDZlNDg=

import { useCallback, useEffect, useRef } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import {
  type Message,
  type Assistant,
  type Checkpoint,
} from "@langchain/langgraph-sdk";
import { v4 as uuidv4 } from "uuid";
import type { UseStreamThread } from "@langchain/langgraph-sdk/react";
import type { TodoItem } from "@/app/types/types";
import { useClient } from "@/providers/ClientProvider";
import { useQueryState } from "nuqs";
import { ContentBlock } from "@langchain/core/messages";
// NOTE  MS80OmFIVnBZMlhsc3JQbGxydm5uN002UkRSYVZRPT06NTQ4NDZlNDg=

export type StateType = {
  messages: Message[];
  todos: TodoItem[];
  files: Record<string, string>;
  email?: {
    id?: string;
    subject?: string;
    page_content?: string;
  };
  ui?: any;
};
// TODO  Mi80OmFIVnBZMlhsc3JQbGxydm5uN002UkRSYVZRPT06NTQ4NDZlNDg=

export function useChat({
  activeAssistant,
  onHistoryRevalidate,
  thread,
  userId,
}: {
  activeAssistant: Assistant | null;
  onHistoryRevalidate?: () => void;
  thread?: UseStreamThread<StateType>;
  userId?: string;
}) {
  const [threadId, setThreadId] = useQueryState("threadId");
  const client = useClient();

  // 构建包含 user_id 的 config
  const buildConfig = useCallback(
    (base?: Record<string, any>) => ({
      ...(base ?? {}),
      recursion_limit: 100,
      ...(userId ? { configurable: { user_id: userId } } : {}),
    }),
    [userId]
  );

  const revalidateHistoryRef = useRef(onHistoryRevalidate);
  const userIdRef = useRef(userId);
  userIdRef.current = userId;

  useEffect(() => {
    revalidateHistoryRef.current = onHistoryRevalidate;
  }, [onHistoryRevalidate]);

  const scheduleHistoryRevalidate = useCallback(() => {
    if (typeof window === "undefined") {
      revalidateHistoryRef.current?.();
      return;
    }

    window.setTimeout(() => {
      revalidateHistoryRef.current?.();
    }, 0);
  }, []);

  // thread 创建后自动写入 user_id metadata
  const handleCreated = useCallback(() => {
    scheduleHistoryRevalidate();
    // useStream 创建新 thread 后，onCreated 触发时 threadId 已更新
    // 通过 setTimeout 确保 threadId 已写入 URL
    window.setTimeout(() => {
      const currentUserId = userIdRef.current;
      if (!currentUserId) return;
      // 从 URL 读取最新的 threadId
      const params = new URLSearchParams(window.location.search);
      const tid = params.get("threadId");
      if (tid) {
        client.threads.update(tid, {
          metadata: { user_id: currentUserId },
        }).catch(console.error);
      }
    }, 0);
  }, [client, scheduleHistoryRevalidate]);

  const stream = useStream<StateType>({
    assistantId: activeAssistant?.assistant_id || "",
    client: client ?? undefined,
    reconnectOnMount: true,
    threadId: threadId ?? null,
    onThreadId: setThreadId,
    defaultHeaders: { "x-auth-scheme": "langsmith" },
    // Enable fetching state history when switching to existing threads
    fetchStateHistory: true,
    // Revalidate thread list after paint to avoid blocking the chat UI
    onFinish: scheduleHistoryRevalidate,
    onError: scheduleHistoryRevalidate,
    onCreated: handleCreated,
    experimental_thread: thread,
  });

  const sendMessage = useCallback(
    (
      content: string,
      contentBlocks?: ContentBlock.Multimodal.Data[]
    ) => {
      // Split blocks: images go into content array as image_url format (OpenAI-compatible),
      // PDFs go into additional_kwargs.attachments (backend parses them)
      const imageBlocks = contentBlocks?.filter((b) => b.type === "image") ?? [];
      const pdfBlocks = contentBlocks?.filter((b) => b.type !== "image") ?? [];

      // Convert image blocks to image_url format required by Doubao/OpenAI-compatible APIs
      const imageUrlBlocks = imageBlocks.map((b) => ({
        type: "image_url" as const,
        image_url: {
          url: `data:${b.mimeType};base64,${b.data}`,
        },
      }));

      const messageContent: Message["content"] =
        imageUrlBlocks.length > 0
          ? ([
              ...(content.trim().length > 0
                ? [{ type: "text" as const, text: content }]
                : []),
              ...imageUrlBlocks,
            ] as Message["content"])
          : content;

      const newMessage: Message = {
        id: uuidv4(),
        type: "human",
        content: messageContent,
        ...(pdfBlocks.length > 0
          ? { additional_kwargs: { attachments: pdfBlocks } }
          : {}),
      };
      stream.submit(
        { messages: [newMessage] },
        {
          optimisticValues: (prev) => ({
            messages: [...(prev.messages ?? []), newMessage],
          }),
          config: buildConfig(activeAssistant?.config),
        }
      );
      // Update thread list immediately when sending a message
      onHistoryRevalidate?.();
    },
    [stream, activeAssistant?.config, onHistoryRevalidate, buildConfig]
  );

  const runSingleStep = useCallback(
    (
      messages: Message[],
      checkpoint?: Checkpoint,
      isRerunningSubagent?: boolean,
      optimisticMessages?: Message[]
    ) => {
      if (checkpoint) {
        stream.submit(undefined, {
          ...(optimisticMessages
            ? { optimisticValues: { messages: optimisticMessages } }
            : {}),
          config: buildConfig(activeAssistant?.config),
          checkpoint: checkpoint,
          ...(isRerunningSubagent
            ? { interruptAfter: ["tools"] }
            : { interruptBefore: ["tools"] }),
        });
      } else {
        stream.submit(
          { messages },
          { config: buildConfig(activeAssistant?.config), interruptBefore: ["tools"] }
        );
      }
    },
    [stream, activeAssistant?.config, buildConfig]
  );

  const setFiles = useCallback(
    async (files: Record<string, string>) => {
      if (!threadId) return;
      // TODO: missing a way how to revalidate the internal state
      // I think we do want to have the ability to externally manage the state
      await client.threads.updateState(threadId, { values: { files } });
    },
    [client, threadId]
  );

  const continueStream = useCallback(
    (hasTaskToolCall?: boolean) => {
      stream.submit(undefined, {
        config: buildConfig(activeAssistant?.config),
        ...(hasTaskToolCall
          ? { interruptAfter: ["tools"] }
          : { interruptBefore: ["tools"] }),
      });
      // Update thread list when continuing stream
      onHistoryRevalidate?.();
    },
    [stream, activeAssistant?.config, onHistoryRevalidate, buildConfig]
  );

  const markCurrentThreadAsResolved = useCallback(() => {
    stream.submit(null, { command: { goto: "__end__", update: null } });
    // Update thread list when marking thread as resolved
    onHistoryRevalidate?.();
  }, [stream, onHistoryRevalidate]);

  const resumeInterrupt = useCallback(
    (value: any) => {
      stream.submit(null, { command: { resume: value } });
      // Update thread list when resuming from interrupt
      onHistoryRevalidate?.();
    },
    [stream, onHistoryRevalidate]
  );

  const stopStream = useCallback(() => {
    stream.stop();
  }, [stream]);

  return {
    stream,
    todos: stream.values.todos ?? [],
    files: stream.values.files ?? {},
    email: stream.values.email,
    ui: stream.values.ui,
    setFiles,
    messages: stream.messages,
    isLoading: stream.isLoading,
    isThreadLoading: stream.isThreadLoading,
    interrupt: stream.interrupt,
    getMessagesMetadata: stream.getMessagesMetadata,
    sendMessage,
    runSingleStep,
    continueStream,
    stopStream,
    markCurrentThreadAsResolved,
    resumeInterrupt,
  };
}
