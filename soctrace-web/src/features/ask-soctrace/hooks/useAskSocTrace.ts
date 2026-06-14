import { useCallback, useState } from "react";
import { askSocTraceService } from "../services/askSocTraceService";
import type { AskSocTraceContext, AskSocTraceMessage, AskSocTraceResponse } from "../types";

function messageId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function useAskSocTrace(context: AskSocTraceContext) {
  const [messages, setMessages] = useState<AskSocTraceMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [sessionId, setSessionId] = useState(() => {
    const existing = window.localStorage.getItem("soctrace.ask.session_id");
    if (existing) return existing;
    const created = messageId();
    window.localStorage.setItem("soctrace.ask.session_id", created);
    return created;
  });
  const [conversationId, setConversationId] = useState(() => window.localStorage.getItem("soctrace.ask.conversation_id") ?? undefined);

  const ask = useCallback(async (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || isThinking) return null;

    const loadingId = messageId();
    const now = new Date().toISOString();
    setMessages((current) => [
      ...current,
      { id: messageId(), role: "user", content: trimmed, createdAt: now },
      {
        id: loadingId,
        role: "assistant",
        content: "SocTrace está analizando los datos...",
        createdAt: new Date().toISOString(),
        loading: true,
        response: {
          answer: "SocTrace está analizando los datos...",
          mode: "simple",
          short_caveat: null,
          summary: "Preparando respuesta.",
          confidence_level: "medium",
          used_tools: [],
          data_origin: [],
          methodological_notes: [],
          audit_id: "loading",
        },
      },
    ]);
    setIsThinking(true);
    try {
      const response = await askSocTraceService.ask(trimmed, { ...context, sessionId, conversationId });
      const nextConversationId = response.conversation_id ?? conversationId;
      const nextSessionId = response.session_id ?? sessionId;
      if (nextConversationId) {
        window.localStorage.setItem("soctrace.ask.conversation_id", nextConversationId);
        setConversationId(nextConversationId);
      }
      if (nextSessionId && nextSessionId !== sessionId) {
        window.localStorage.setItem("soctrace.ask.session_id", nextSessionId);
        setSessionId(nextSessionId);
      }
      setMessages((current) => current.map((message) => (
        message.id === loadingId
          ? { id: loadingId, role: "assistant", content: response.answer, createdAt: new Date().toISOString(), response }
          : message
      )));
      return response;
    } catch {
      const response: AskSocTraceResponse = {
        answer: "No he podido completar la consulta en este momento. Inténtalo de nuevo.",
        mode: "simple" as const,
        short_caveat: null,
        summary: "La consulta no se ha completado.",
        confidence_level: "low" as const,
        used_tools: [],
        data_origin: [],
        methodological_notes: [],
        audit_id: "not-available",
      };
      setMessages((current) => current.map((message) => (
        message.id === loadingId
          ? {
              id: loadingId,
              role: "assistant",
              content: response.answer,
              createdAt: new Date().toISOString(),
              response,
              error: response.answer,
            }
          : message
      )));
      return response;
    } finally {
      setIsThinking(false);
    }
  }, [context, conversationId, isThinking, sessionId]);

  const newConversation = useCallback(() => {
    const created = messageId();
    window.localStorage.setItem("soctrace.ask.session_id", created);
    window.localStorage.removeItem("soctrace.ask.conversation_id");
    setSessionId(created);
    setConversationId(undefined);
    setMessages([]);
  }, []);

  return { messages, isThinking, ask, sessionId, conversationId, newConversation };
}
