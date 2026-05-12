from __future__ import annotations

import sys
from concurrent import futures
from pathlib import Path
from typing import Any

import grpc

from common.config import Settings
from common.logging import get_logger
from pipeline.latest_recalculation import run_latest_recalculation
from rag.analyst_service import answer_question
from rag.lsi_rag_indexer import rebuild_lsi_rag_index

logger = get_logger(__name__)

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "gen" / "python"
if GEN.exists():
    sys.path.insert(0, str(GEN))

try:
    from liquidity.v1 import analyst_pb2, backtest_pb2, common_pb2, lsi_pb2, modules_pb2, liquidity_pb2_grpc
except Exception as exc:  # pragma: no cover
    analyst_pb2 = backtest_pb2 = common_pb2 = lsi_pb2 = modules_pb2 = liquidity_pb2_grpc = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

STATUS_MAP = {"green": 1, "yellow": 2, "red": 3, "STATUS_GREEN": 1, "STATUS_YELLOW": 2, "STATUS_RED": 3}
MODULE_MAP = {"M1": 1, "M1_RESERVES": 1, "M2": 2, "M2_REPO": 2, "M3": 3, "M3_OFZ": 3, "M4": 4, "M4_TAX": 4, "M5": 5, "M5_TREASURY": 5, "SYSTEM": 0}
MODULE_CODE = {1: "M1", 2: "M2", 3: "M3", 4: "M4", 5: "M5"}


def _status(value: str) -> int:
    return STATUS_MAP.get(str(value), 0)


def _module(value: str) -> int:
    return MODULE_MAP.get(str(value), 0)


def _lsi_response(result: Any):
    return lsi_pb2.LSIResponse(
        date=result.date,
        lsi=float(result.lsi),
        status=_status(result.status),
        confidence=float(result.confidence or 0.0),
        contributions=[
            lsi_pb2.ModuleContribution(
                module_id=_module(c.get("module_id")),
                module_name=str(c.get("module_name", c.get("module_id", ""))),
                contribution_value=float(c.get("contribution_value", 0.0)),
                contribution_percent=float(c.get("contribution_percent", 0.0)),
            ) for c in result.contributions
        ],
        shap_values=[
            lsi_pb2.ShapValue(
                feature_name=str(item.get("feature_name", "")),
                module_id=_module(item.get("module_id")),
                value=float(item.get("value", 0.0)),
                abs_value=float(item.get("abs_value", 0.0)),
            ) for item in getattr(result, "shap_values", [])
        ],
        active_flags=[
            modules_pb2.ActiveFlag(
                flag_name=str(f.get("flag_name", "")),
                module_id=_module(f.get("module_id")),
                description=str(f.get("description", "")),
                severity=float(f.get("severity", 0.0)),
            ) for f in result.active_flags
        ],
        forecast=[],
        auto_comment=result.auto_comment or "",
    )


class LiquidityServicer(liquidity_pb2_grpc.LiquidityServiceServicer):
    def RecalculateLSI(self, request, context):
        result = run_latest_recalculation(
            date=request.date or None,
            force_reload_sources=request.force_reload_sources,
            recalculate_shap=request.recalculate_shap,
            regenerate_comment=request.regenerate_comment,
        )
        return lsi_pb2.RecalculateLSIResponse(result=_lsi_response(result), updated_sources=result.updated_sources)

    def GetCurrentLSI(self, request, context):
        try:
            from common.database import Database
            from repositories import LSIRepository, ModuleSignalsRepository, ShapRepository

            db = Database()
            db.connect()
            try:
                lsi_repo = LSIRepository(db)
                signals_repo = ModuleSignalsRepository(db)
                shap_repo = ShapRepository(db)
                latest = lsi_repo.get_latest_lsi()
                if latest is None:
                    result = run_latest_recalculation(recalculate_shap=request.include_shap, regenerate_comment=request.include_comment)
                    return _lsi_response(result)
                contributions = lsi_repo.get_module_contributions(latest["id"])
                shap_values = shap_repo.get_top_shap_values(latest["id"], limit=20) if request.include_shap else []
                flags = signals_repo.get_active_flags(flag_date=latest["calculation_date"])
            finally:
                db.close()

            class Obj:
                pass
            obj = Obj()
            obj.date = latest["calculation_date"].isoformat()
            obj.lsi = float(latest["lsi"])
            obj.status = str(latest["status"])
            obj.confidence = float(latest.get("confidence") or 0.0)
            obj.auto_comment = latest.get("auto_comment") if request.include_comment else ""
            obj.contributions = contributions
            obj.shap_values = shap_values
            obj.active_flags = flags
            return _lsi_response(obj)
        except Exception:
            result = run_latest_recalculation(recalculate_shap=request.include_shap, regenerate_comment=request.include_comment)
            return _lsi_response(result)

    def GetLSIHistory(self, request, context):
        import pandas as pd
        points = []
        try:
            from common.database import Database
            from repositories import LSIRepository

            db = Database()
            db.connect()
            try:
                repo = LSIRepository(db)
                from_value = getattr(request.range, "from") if request.HasField("range") else "2021-01-01"
                to_value = getattr(request.range, "to") if request.HasField("range") else pd.Timestamp.today().date().isoformat()
                limit = request.pagination.limit or 500
                offset = request.pagination.offset or 0
                history = repo.get_lsi_history(pd.to_datetime(from_value).date(), pd.to_datetime(to_value).date(), limit=limit, offset=offset)
            finally:
                db.close()
            for row in history:
                points.append(lsi_pb2.LSIHistoryPoint(date=row["calculation_date"].isoformat(), lsi=float(row.get("lsi", 0.0)), status=_status(row.get("status", "green")), confidence=float(row.get("confidence", 0.0) or 0.0)))
        except Exception:
            pass
        return lsi_pb2.GetLSIHistoryResponse(points=points)

    def GetModuleSignals(self, request, context):
        signals = []
        active_flags = []
        try:
            import pandas as pd
            from common.database import Database
            from repositories import ModuleSignalsRepository
            db = Database()
            db.connect()
            try:
                repo = ModuleSignalsRepository(db)
                module_code = MODULE_CODE.get(int(request.module_id), "M1")
                module_id = {"M1": "M1_RESERVES", "M2": "M2_REPO", "M3": "M3_OFZ", "M4": "M4_TAX", "M5": "M5_TREASURY"}[module_code]
                from_value = getattr(request.range, "from") if request.HasField("range") else "2021-01-01"
                to_value = getattr(request.range, "to") if request.HasField("range") else datetime.utcnow().date().isoformat()
                rows = repo.get_signals(module_id, pd.to_datetime(from_value).date(), pd.to_datetime(to_value).date())
                flags = repo.get_active_flags(module_id=module_id)
            finally:
                db.close()
            for row in rows:
                signals.append(modules_pb2.ModuleSignal(date=row["signal_date"].isoformat(), module_id=request.module_id, signal_name=str(row["signal_name"]), raw_value=float(row.get("raw_value") or 0.0), mad_score=float(row.get("mad_score") or 0.0), flag=bool(row.get("flag")), unit=str(row.get("unit") or "")))
            for row in flags:
                active_flags.append(modules_pb2.ActiveFlag(flag_name=str(row["flag_name"]), module_id=request.module_id, description=str(row.get("description") or ""), severity=float(row.get("severity") or 0.0)))
        except Exception:
            pass
        return modules_pb2.GetModuleSignalsResponse(module_id=request.module_id, signals=signals, active_flags=active_flags)


    def GetBacktest(self, request, context):
        import pandas as pd
        from pipeline.history_bootstrap import bootstrap_full_history

        def _episode_range(episode: int) -> tuple[str, str]:
            if episode == backtest_pb2.STRESS_EPISODE_DECEMBER_2014:
                return "2014-12-01", "2014-12-31"
            if episode == backtest_pb2.STRESS_EPISODE_FEBRUARY_MARCH_2022:
                return "2022-02-01", "2022-03-31"
            if episode == backtest_pb2.STRESS_EPISODE_AUGUST_2023:
                return "2023-08-01", "2023-08-31"
            if request.HasField("custom_range"):
                return getattr(request.custom_range, "from") or "2021-01-01", request.custom_range.to or pd.Timestamp.today().date().isoformat()
            return "2021-01-01", pd.Timestamp.today().date().isoformat()

        date_from, date_to = _episode_range(int(request.episode))
        path = ROOT.parents[0] / "data" / "processed" / "dashboard" / "lsi_dashboard.csv"
        if not path.exists():
            bootstrap_full_history(persist=True)

        df = pd.DataFrame(columns=["date", "LSI", "status", "confidence"])
        if path.exists():
            df = pd.read_csv(path)
        if not df.empty and "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"]).sort_values("date")
            df = df[(df["date"] >= pd.to_datetime(date_from)) & (df["date"] <= pd.to_datetime(date_to))]

        points = [
            lsi_pb2.LSIHistoryPoint(
                date=row["date"].date().isoformat(),
                lsi=float(row.get("LSI", 0.0)),
                status=_status(row.get("status", "green")),
                confidence=float(row.get("confidence", 0.0)),
            )
            for _, row in df.iterrows()
        ]

        metrics = []
        events = []
        conclusion = "Нет данных LSI для выбранного периода. Сначала загрузите историю через BaseParser historical mode."
        if points:
            values = [p.lsi for p in points]
            metrics = [
                backtest_pb2.BacktestMetric(name="points", value=float(len(values)), unit="count"),
                backtest_pb2.BacktestMetric(name="average_lsi", value=float(sum(values) / len(values)), unit="lsi_points"),
                backtest_pb2.BacktestMetric(name="max_lsi", value=float(max(values)), unit="lsi_points"),
                backtest_pb2.BacktestMetric(name="min_lsi", value=float(min(values)), unit="lsi_points"),
            ]
            max_point = max(points, key=lambda p: p.lsi)
            events = [
                backtest_pb2.BacktestEvent(
                    date=max_point.date,
                    title="Пик LSI в выбранном периоде",
                    description="Максимальное значение Liquidity Stress Index внутри backtest range.",
                    lsi=max_point.lsi,
                    status=max_point.status,
                )
            ]
            conclusion = f"Backtest построен по истории LSI за {date_from}..{date_to}: точек={len(values)}, max={max(values):.2f}, avg={sum(values)/len(values):.2f}."

        avg_contribs = []
        # If dashboard history has contribution columns, expose period averages.
        contrib_columns = [
            ("M1_contribution", 1, "M1_RESERVES"),
            ("M2_contribution", 2, "M2_REPO"),
            ("M3_contribution", 3, "M3_OFZ"),
            ("M4_effect", 4, "M4_TAX"),
            ("M5_contribution", 5, "M5_TREASURY"),
        ]
        for col, module_id, name in contrib_columns:
            if col in df.columns and not df.empty:
                value = float(pd.to_numeric(df[col], errors="coerce").fillna(0.0).mean())
                avg_contribs.append(lsi_pb2.ModuleContribution(module_id=module_id, module_name=name, contribution_value=value, contribution_percent=0.0))

        return backtest_pb2.BacktestResponse(
            episode=request.episode,
            range=common_pb2.DateRange(**{"from": date_from, "to": date_to}),
            lsi_history=points,
            metrics=metrics,
            events=events,
            average_contributions=avg_contribs,
            conclusion=conclusion,
        )

    def GetAllModulesSnapshot(self, request, context):
        try:
            from common.database import Database
            from repositories import ModuleSignalsRepository
            db = Database()
            db.connect()
            try:
                repo = ModuleSignalsRepository(db)
                latest_rows = repo.get_latest_signals()
            finally:
                db.close()
            signal_map: dict[str, list[Any]] = {}
            latest_date = ""
            for row in latest_rows:
                latest_date = max(latest_date, row["signal_date"].isoformat())
                signal_map.setdefault(row["module_id"], []).append(row)
        except Exception:
            signal_map = {}
            latest_date = ""
        modules = []
        for n in range(1, 6):
            code = MODULE_CODE[n]
            signals = []
            module_id = {"M1": "M1_RESERVES", "M2": "M2_REPO", "M3": "M3_OFZ", "M4": "M4_TAX", "M5": "M5_TREASURY"}[code]
            for row in signal_map.get(module_id, []):
                signals.append(modules_pb2.ModuleSignal(date=row["signal_date"].isoformat(), module_id=n, signal_name=str(row["signal_name"]), raw_value=float(row.get("raw_value") or 0.0), mad_score=float(row.get("mad_score") or 0.0), flag=bool(row.get("flag")), unit=str(row.get("unit") or "")))
            modules.append(modules_pb2.ModuleSnapshot(module_id=n, module_name=code, module_score=0.0, signals=signals, active_flags=[]))
        return modules_pb2.GetAllModulesSnapshotResponse(date=latest_date, modules=modules)

    def GenerateAutoComment(self, request, context):
        module_contributions = [
            f"{item.name}={item.value:.2f}"
            for item in request.module_contributions
        ]
        active_flags = ", ".join(request.active_flags) if request.active_flags else "нет"
        upcoming_events = ", ".join(request.upcoming_events) if request.upcoming_events else "нет"
        prompt = (
            f"Текущий LSI: {request.lsi:.2f}. Статус: {_status(request.status).lower()}. "
            f"Вклады модулей: {', '.join(module_contributions) or 'нет'}. "
            f"Активные флаги: {active_flags}. Ближайшие события: {upcoming_events}."
        )
        try:
            from llm.client import LLMClient
            comment = (LLMClient().generate(
                "Сформируй краткий аналитический комментарий для dashboard RU Liquidity Sentinel. "
                "Пиши на русском, опирайся только на данные.\n\n" + prompt
            ) or "").strip()
        except Exception:
            comment = prompt
        return analyst_pb2.AutoCommentResponse(comment=comment, retrospective="", outlook="")

    def ChatAnalyst(self, request, context):
        try:
            rebuild_lsi_rag_index(limit_days=30)
        except Exception:
            pass
        result = answer_question(request.user_message)
        contexts = []
        for idx, item in enumerate(result.get("citations", [])[:10]):
            contexts.append(analyst_pb2.RetrievedContext(
                source_type="rag",
                title=f"context_{idx + 1}",
                content=str(item),
                relevance=max(0.1, 1.0 - idx * 0.1),
            ))
        return analyst_pb2.ChatResponse(
            session_id=request.session_id or "",
            answer=result.get("answer", "Недостаточно данных для ответа."),
            contexts=contexts,
        )



def bootstrap_history_on_startup() -> None:
    import os
    enabled = os.getenv("RLS_BOOTSTRAP_HISTORY_ON_STARTUP", "true").strip().lower() in {"1", "true", "yes", "y", "on"}
    if not enabled:
        logger.info("Startup LSI history bootstrap disabled")
        return
    try:
        from pipeline.history_bootstrap import bootstrap_full_history
        result = bootstrap_full_history(persist=True)
        logger.info("Startup LSI history bootstrap result: %s", result)
    except Exception as exc:  # pragma: no cover
        logger.warning("Startup LSI history bootstrap failed: %s", exc, exc_info=True)

def train_lsi_model_on_startup() -> None:
    """Train the IsolationForest LSI model and persist artifacts so the
    history bootstrap (and live snapshot predictions) use the model
    instead of the explainable-formula fallback."""
    try:
        from lsi_engine import iso_model
        result = iso_model.bootstrap_train_if_needed()
        logger.info("LSI model startup training result: %s", result)
    except Exception as exc:  # pragma: no cover
        logger.warning("LSI model startup training failed: %s", exc, exc_info=True)


def serve() -> None:
    if IMPORT_ERROR is not None:
        raise RuntimeError(f"Python protobuf stubs are not generated or importable: {IMPORT_ERROR}")
    settings = Settings()
    train_lsi_model_on_startup()
    bootstrap_history_on_startup()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    liquidity_pb2_grpc.add_LiquidityServiceServicer_to_server(LiquidityServicer(), server)
    server.add_insecure_port(f"[::]:{settings.ml_grpc_port}")
    server.start()
    logger.info("Starting gRPC ML service on port %s", settings.ml_grpc_port)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
