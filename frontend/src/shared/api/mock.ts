import type { AnalystChatResponse, AutoCommentResponse } from "@/shared/types/analyst";
import type { BacktestResponse } from "@/shared/types/backtest";
import type { DashboardResponse } from "@/shared/types/dashboard";
import type { LsiHistoryResponse } from "@/shared/types/lsi";
import type { ModuleSignalsResponse, ModulesResponse, ModulesSnapshotResponse } from "@/shared/types/modules";
import type { ScenarioResponse } from "@/shared/types/scenario";

export const mockDashboard: DashboardResponse = {
  date: "2026-05-08",
  lsi: 67.5,
  status: "yellow",
  confidence: 0.82,
  contributions: [
    { module_id: "M2_REPO", module_name: "Аукционы репо ЦБ", contribution_value: 24, contribution_percent: 35.5 },
    { module_id: "M5_TREASURY", module_name: "Средства федерального казначейства", contribution_value: 16.2, contribution_percent: 24.1 },
    { module_id: "M4_TAX", module_name: "Налоговый период и сезонность", contribution_value: 11.4, contribution_percent: 16.9 },
    { module_id: "M3_OFZ", module_name: "Размещение ОФЗ", contribution_value: 9.1, contribution_percent: 13.5 },
    { module_id: "M1_RESERVES", module_name: "Усреднение обязательных резервов", contribution_value: 6.8, contribution_percent: 10.0 }
  ],
  shap_values: [
    { feature_name: "M2_repo.cover_ratio", module_id: "M2_REPO", value: 8.4, abs_value: 8.4 },
    { feature_name: "treasury_delta_week", module_id: "M5_TREASURY", value: 6.2, abs_value: 6.2 },
    { feature_name: "tax_week_flag", module_id: "M4_TAX", value: 4.8, abs_value: 4.8 }
  ],
  active_flags: [
    { flag_name: "Flag_Demand", module_id: "M2_REPO", description: "Cover ratio репо выше порога", severity: 0.85 },
    { flag_name: "Flag_TaxWeek", module_id: "M4_TAX", description: "Налоговая неделя усиливает изъятие ликвидности", severity: 0.72 }
  ],
  forecast: [
    { horizon: "1d", target_date: "2026-05-09", lsi: 69.1, status: "yellow", confidence: 0.81 },
    { horizon: "3d", target_date: "2026-05-11", lsi: 74.2, status: "red", confidence: 0.76 },
    { horizon: "7d", target_date: "2026-05-15", lsi: 71.3, status: "red", confidence: 0.7 }
  ],
  auto_comment:
    "Основное давление сейчас формируют аукционы репо и казначейские потоки. Если налоговая неделя усилится, LSI может перейти в красную зону в горизонте 3 дней."
};

export const mockLsiHistory: LsiHistoryResponse = {
  points: Array.from({ length: 20 }, (_, index) => ({
    date: `2026-04-${String(index + 10).padStart(2, "0")}`,
    lsi: 44 + index * 1.2 + (index % 4 === 0 ? 4 : 0),
    status: index > 16 ? "yellow" : "green",
    confidence: 0.72 + index * 0.005
  }))
};

export const mockModules: ModulesResponse = {
  modules: [
    {
      module_id: "M1_RESERVES",
      module_name: "Усреднение обязательных резервов",
      description: "Оценивает напряжение через спред обязательных резервов и RUONIA."
    },
    {
      module_id: "M2_REPO",
      module_name: "Аукционы репо ЦБ",
      description: "Фокус на cover ratio, спросе и краткосрочном дефиците ликвидности."
    },
    {
      module_id: "M3_OFZ",
      module_name: "Размещение ОФЗ",
      description: "Сигнализирует по слабому спросу и изменению условий финансирования."
    },
    {
      module_id: "M4_TAX",
      module_name: "Налоговый период и сезонность",
      description: "Модуль сезонных паттернов и налоговой недели."
    },
    {
      module_id: "M5_TREASURY",
      module_name: "Средства федерального казначейства",
      description: "Модуль потоков казначейства и недельных оттоков."
    }
  ]
};

export const mockModulesSnapshot: ModulesSnapshotResponse = {
  date: "2026-05-08",
  modules: mockModules.modules.map((module, index) => ({
    module_id: module.module_id,
    module_name: module.module_name,
    module_score: 49 + index * 8,
    signals: [],
    active_flags:
      index % 2 === 0
        ? []
        : [
            {
              flag_name: "Flag_Demo",
              module_id: module.module_id,
              description: "Демонстрационный флаг стресса",
              severity: 0.55 + index * 0.05
            }
          ]
  }))
};

export const mockModuleSignals: ModuleSignalsResponse = {
  module_id: "M2_REPO",
  signals: Array.from({ length: 12 }, (_, index) => ({
    date: `2022-02-${String(index + 20).padStart(2, "0")}`,
    module_id: "M2_REPO",
    signal_name: "MAD_score_cover",
    raw_value: 1.1 + index * 0.2,
    mad_score: 0.8 + index * 0.16,
    flag: index > 7,
    unit: "ratio"
  })),
  active_flags: [
    { flag_name: "Flag_Demand", module_id: "M2_REPO", description: "Спрос на репо выше порога", severity: 0.83 }
  ]
};

export const mockScenarioResult: ScenarioResponse = {
  base_date: "2026-05-08",
  base_lsi: 58.2,
  base_status: "yellow",
  scenario_lsi: 84.1,
  scenario_status: "red",
  delta_lsi: 25.9,
  changed_contributions: mockDashboard.contributions,
  scenario_shap_values: mockDashboard.shap_values,
  explanation: "Сценарий усиливает давление через казначейский отток и репо-канал, из-за чего индекс переходит в красную зону."
};

export const mockBacktest: BacktestResponse = {
  episode: "february_march_2022",
  range: { from: "2022-02-01", to: "2022-03-31" },
  lsi_history: Array.from({ length: 18 }, (_, index) => ({
    date: `2022-02-${String(index + 10).padStart(2, "0")}`,
    lsi: 42 + index * 2.3,
    status: index > 10 ? "yellow" : "green",
    confidence: 0.71 + index * 0.01
  })),
  metrics: [
    { name: "lead_time_days", value: 3, unit: "days" },
    { name: "peak_lsi", value: 81.4 },
    { name: "alerts_count", value: 6 }
  ],
  events: [
    { date: "2022-02-24", title: "Shock day", description: "Резкий скачок спроса на ликвидность", severity: "high" },
    { date: "2022-03-01", title: "Policy response", description: "Меры поддержки стабилизировали краткосрочный рынок", severity: "medium" }
  ],
  average_contributions: mockDashboard.contributions,
  conclusion: "Backtest показывает, что система улавливает рост напряжения за несколько дней до пика."
};

export const mockAnalystChat: AnalystChatResponse = {
  session_id: "demo-session-1",
  answer: "В августе 2023 рост LSI был связан с одновременным давлением налогового периода и ухудшением условий фондирования на рынке репо.",
  contexts: [
    {
      source_type: "lsi_history",
      title: "LSI history August 2023",
      content: "LSI вырос с 42 до 71 на фоне сжатия ликвидности и усиления налогового окна.",
      relevance: 0.91
    }
  ]
};

export const mockAutoComment: AutoCommentResponse = {
  comment: "Текущая конфигурация сигналов указывает на умеренный стресс с риском дальнейшего роста.",
  retrospective: "Вклад репо и казначейства усиливался последние несколько торговых дней.",
  outlook: "Ближайший горизонт 3-7 дней требует внимания к налоговой неделе и спросу на репо."
};
