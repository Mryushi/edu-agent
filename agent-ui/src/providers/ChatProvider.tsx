"use client";

import { ReactNode, createContext, useContext } from "react";
import { Assistant } from "@langchain/langgraph-sdk";
import { type StateType, useChat } from "@/app/hooks/useChat";
import type { UseStreamThread } from "@langchain/langgraph-sdk/react";
// TODO  MC8yOmFIVnBZMlhsc3JQbGxydm5uN002ZVRSbWN3PT06YjMyY2JiMWM=

interface ChatProviderProps {
  children: ReactNode;
  activeAssistant: Assistant | null;
  onHistoryRevalidate?: () => void;
  thread?: UseStreamThread<StateType>;
  userId?: string;
}

export function ChatProvider({
  children,
  activeAssistant,
  onHistoryRevalidate,
  thread,
  userId,
}: ChatProviderProps) {
  const chat = useChat({ activeAssistant, onHistoryRevalidate, thread, userId });
  return <ChatContext.Provider value={chat}>{children}</ChatContext.Provider>;
}

export type ChatContextType = ReturnType<typeof useChat>;

export const ChatContext = createContext<ChatContextType | undefined>(
  undefined
);

export function useChatContext() {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error("useChatContext must be used within a ChatProvider");
  }
  return context;
}
