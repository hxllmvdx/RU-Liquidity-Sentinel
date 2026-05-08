"use client";

import { Button } from "@/components/ui/button";

const suggestions = [
  "Почему вырос LSI в августе 2023?",
  "Какие модули дали главный вклад сейчас?",
  "Похож ли текущий период на февраль 2022?",
  "Что будет при усилении оттока казначейства?",
  "Как налоговая неделя влияет на LSI?"
];

export function SuggestedQuestions({ onSelect }: { onSelect: (value: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {suggestions.map((item) => (
        <Button key={item} onClick={() => onSelect(item)} type="button" variant="secondary">
          {item}
        </Button>
      ))}
    </div>
  );
}
