import { apiRequest } from "@/shared/api/client";
import { mockAnalystChat, mockAutoComment } from "@/shared/api/mock";
import type { AnalystChatRequest, AnalystChatResponse, AutoCommentRequest, AutoCommentResponse } from "@/shared/types/analyst";

export function sendAnalystMessage(request: AnalystChatRequest): Promise<AnalystChatResponse> {
  return apiRequest({
    path: "/api/analyst/chat",
    init: {
      method: "POST",
      body: JSON.stringify(request)
    },
    mockData: mockAnalystChat
  });
}

export function generateAutoComment(request: AutoCommentRequest): Promise<AutoCommentResponse> {
  return apiRequest({
    path: "/api/analyst/comment",
    init: {
      method: "POST",
      body: JSON.stringify(request)
    },
    mockData: mockAutoComment
  });
}
