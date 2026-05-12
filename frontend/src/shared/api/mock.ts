import type { AnalystChatResponse, AutoCommentResponse } from "@/shared/types/analyst";
import type { BacktestResponse } from "@/shared/types/backtest";
import type { DashboardResponse } from "@/shared/types/dashboard";
import type { LsiHistoryResponse } from "@/shared/types/lsi";
import type { ModuleSignalsResponse, ModulesResponse, ModulesSnapshotResponse } from "@/shared/types/modules";
import type { ScenarioResponse } from "@/shared/types/scenario";

export const mockDashboard: DashboardResponse = {
  date: new Date().toISOString().slice(0, 10),
  lsi: 0,
  status: "green",
  confidence: 0,
  contributions: [],
  shap_values: [],
  active_flags: [],
  forecast: [],
  auto_comment: "Mock-режим включён: реальные данные недоступны. Отключи NEXT_PUBLIC_USE_MOCKS для production-like dashboard."
};

export const mockLsiHistory: LsiHistoryResponse = { points: [] };

export const mockModules: ModulesResponse = {
  modules: [
    { module_id: "M1_RESERVES", module_name: "Усреднение обязательных резервов", description: "Оценивает напряжение через спред обязательных резервов и RUONIA." },
    { module_id: "M2_REPO", module_name: "Аукционы репо ЦБ", description: "Фокус на cover ratio, спросе и краткосрочном дефиците ликвидности." },
    { module_id: "M3_OFZ", module_name: "Размещение ОФЗ", description: "Сигнализирует по слабому спросу и изменению условий финансирования." },
    { module_id: "M4_TAX", module_name: "Налоговый период и сезонность", description: "Модуль сезонных паттернов и налоговой недели." },
    { module_id: "M5_TREASURY", module_name: "Средства федерального казначейства", description: "Модуль потоков казначейства и недельных оттоков." }
  ]
};

export const mockModulesSnapshot: ModulesSnapshotResponse = {
  date: mockDashboard.date,
  modules: mockModules.modules.map((module) => ({ ...module, module_score: 0, signals: [], active_flags: [] }))
};

export const mockModuleSignals: ModuleSignalsResponse = {
  module_id: "M2_REPO",
  signals: [],
  active_flags: []
};

export const mockScenarioResult: ScenarioResponse = {
  base_date: mockDashboard.date,
  base_lsi: 0,
  base_status: "green",
  scenario_lsi: 0,
  scenario_status: "green",
  delta_lsi: 0,
  changed_contributions: [],
  scenario_shap_values: [],
  explanation: "Mock-режим: сценарий не рассчитан."
};

export const mockBacktest: BacktestResponse = {
  episode: "custom",
  range: { from: "", to: "" },
  lsi_history: [],
  metrics: [],
  events: [],
  average_contributions: [],
  conclusion: "Mock-режим: backtest не рассчитан."
};

export const mockAnalystChat: AnalystChatResponse = {
  session_id: "mock-session",
  answer: "Mock-режим: RAG-контекст недоступен.",
  contexts: []
};

export const mockAutoComment: AutoCommentResponse = {
  comment: "Mock-режим: автокомментарий не рассчитан.",
  retrospective: "",
  outlook: ""
};
