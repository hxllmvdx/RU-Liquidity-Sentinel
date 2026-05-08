import type { ModuleId } from "@/shared/types/common";

export const MODULE_META: Record<ModuleId, { shortName: string; description: string }> = {
  M1_RESERVES: {
    shortName: "М1 Усреднение обязательных резервов",
    description: "Оценивает напряжение через обязательные резервы, RUONIA и связанные спрэды."
  },
  M2_REPO: {
    shortName: "М2 Аукционы репо ЦБ",
    description: "Отслеживает аукционы репо, cover ratio и дефицит краткосрочной ликвидности."
  },
  M3_OFZ: {
    shortName: "М3 Размещение ОФЗ",
    description: "Подсвечивает давление на рынок через слабый спрос на ОФЗ и ценовые аномалии."
  },
  M4_TAX: {
    shortName: "М4 Налоговый период и сезонность",
    description: "Учитывает налоговую неделю и сезонные паттерны изъятия ликвидности."
  },
  M5_TREASURY: {
    shortName: "М5 Средства федерального казначейства",
    description: "Показывает влияние потоков казначейства и недельных оттоков на систему."
  }
};

export const MODULE_IDS: ModuleId[] = ["M1_RESERVES", "M2_REPO", "M3_OFZ", "M4_TAX", "M5_TREASURY"];
