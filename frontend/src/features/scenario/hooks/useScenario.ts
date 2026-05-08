"use client";

import { useMutation } from "@tanstack/react-query";
import { runScenario } from "@/shared/api/scenario";

export function useScenario() {
  return useMutation({
    mutationFn: runScenario
  });
}
