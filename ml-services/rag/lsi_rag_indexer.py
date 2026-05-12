from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from common.database import Database
from repositories import LSIRepository, ModuleSignalsRepository, RagRepository, ShapRepository


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def rebuild_lsi_rag_index(limit_days: int = 30) -> dict[str, int]:
    db = Database()
    db.connect()
    counts = {"documents": 0}
    try:
        lsi_repo = LSIRepository(db)
        signals_repo = ModuleSignalsRepository(db)
        shap_repo = ShapRepository(db)
        rag_repo = RagRepository(db)

        latest = lsi_repo.get_latest_lsi()
        if latest is None:
            return counts

        latest_date = latest["calculation_date"]
        from_date = latest_date - timedelta(days=limit_days)
        history = lsi_repo.get_lsi_history(from_date, latest_date, limit=limit_days + 5, offset=0)
        contributions = lsi_repo.get_module_contributions(latest["id"])
        shap_values = shap_repo.get_top_shap_values(latest["id"], limit=15)
        active_flags = signals_repo.get_active_flags(flag_date=latest_date)
        latest_signals = signals_repo.get_latest_signals()

        rag_repo.delete_documents_by_source("lsi_current")
        rag_repo.delete_documents_by_source("lsi_history")
        rag_repo.delete_documents_by_source("lsi_contributions")
        rag_repo.delete_documents_by_source("lsi_shap")
        rag_repo.delete_documents_by_source("lsi_flags")
        rag_repo.delete_documents_by_source("lsi_modules_snapshot")

        docs = [
            {
                "source_type": "lsi_current",
                "source_id": latest_date.isoformat(),
                "title": f"Текущий LSI на {latest_date.isoformat()}",
                "content": (
                    f"Текущий LSI {float(latest['lsi']):.2f}. Статус {latest['status']}. "
                    f"Confidence {float(latest.get('confidence') or 0.0):.2f}. "
                    f"Автокомментарий: {latest.get('auto_comment') or 'нет'}."
                ),
                "metadata": {"calculation_date": latest_date.isoformat()},
            },
            {
                "source_type": "lsi_history",
                "source_id": latest_date.isoformat(),
                "title": f"История LSI до {latest_date.isoformat()}",
                "content": "Исторический ряд LSI: " + "; ".join(
                    f"{row['calculation_date'].isoformat()} LSI={float(row['lsi']):.2f} status={row['status']} conf={float(row.get('confidence') or 0.0):.2f}"
                    for row in history[-30:]
                ),
                "metadata": {"rows": len(history)},
            },
            {
                "source_type": "lsi_contributions",
                "source_id": latest_date.isoformat(),
                "title": f"Вклады модулей LSI на {latest_date.isoformat()}",
                "content": "Вклады модулей: " + "; ".join(
                    f"{item['module_id']} value={float(item['contribution_value']):.4f} percent={float(item.get('contribution_percent') or 0.0):.2f}"
                    for item in contributions
                ),
                "metadata": {"modules": [item["module_id"] for item in contributions]},
            },
            {
                "source_type": "lsi_shap",
                "source_id": latest_date.isoformat(),
                "title": f"SHAP драйверы LSI на {latest_date.isoformat()}",
                "content": "SHAP-like драйверы: " + "; ".join(
                    f"{item['feature_name']} module={item['module_id']} value={float(item['value']):.4f} abs={float(item['abs_value']):.4f}"
                    for item in shap_values
                ),
                "metadata": {"count": len(shap_values)},
            },
            {
                "source_type": "lsi_flags",
                "source_id": latest_date.isoformat(),
                "title": f"Активные флаги на {latest_date.isoformat()}",
                "content": "Активные флаги: " + (
                    "; ".join(
                        f"{item['module_id']} {item['flag_name']} severity={float(item.get('severity') or 0.0):.2f} description={item.get('description') or ''}"
                        for item in active_flags
                    ) if active_flags else "нет активных флагов"
                ),
                "metadata": {"count": len(active_flags)},
            },
            {
                "source_type": "lsi_modules_snapshot",
                "source_id": latest_date.isoformat(),
                "title": f"Последний snapshot сигналов модулей на {latest_date.isoformat()}",
                "content": "Последние сигналы модулей: " + "; ".join(
                    f"{item['module_id']} {item['signal_name']} raw={item.get('raw_value')} mad={item.get('mad_score')} flag={item.get('flag')}"
                    for item in latest_signals
                ),
                "metadata": {"count": len(latest_signals)},
            },
        ]

        for doc in docs:
            rag_repo.upsert_document(
                source_type=doc["source_type"],
                source_id=doc["source_id"],
                title=doc["title"],
                content=doc["content"],
                metadata=doc["metadata"],
                embedding=None,
            )
            counts["documents"] += 1
        return counts
    finally:
        db.close()
