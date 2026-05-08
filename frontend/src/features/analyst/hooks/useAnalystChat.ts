"use client";

import { useMutation } from "@tanstack/react-query";
import { sendAnalystMessage } from "@/shared/api/analyst";

export function useAnalystChat() {
  return useMutation({
    mutationFn: sendAnalystMessage
  });
}
