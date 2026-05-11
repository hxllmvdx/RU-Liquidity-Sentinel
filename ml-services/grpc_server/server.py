from __future__ import annotations

import sys
from concurrent import futures
from pathlib import Path
from typing import Any

import grpc

from common.config import Settings
from common.logging import get_logger
from pipeline.latest_recalculation import run_latest_recalculation

logger = get_logger(__name__)

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "gen" / "python"
if GEN.exists():
    sys.path.insert(0, str(GEN))

try:
    from liquidity.v1 import common_pb2, lsi_pb2, modules_pb2, liquidity_pb2_grpc
except Exception as exc:  # pragma: no cover
    common_pb2 = lsi_pb2 = modules_pb2 = liquidity_pb2_grpc = None
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
        shap_values=[],
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
        result = run_latest_recalculation(recalculate_shap=request.include_shap, regenerate_comment=request.include_comment)
        return _lsi_response(result)

    def GetLSIHistory(self, request, context):
        import pandas as pd
        path = ROOT.parents[0] / "data" / "processed" / "dashboard" / "lsi_dashboard.csv"
        points = []
        if path.exists():
            df = pd.read_csv(path)
            for _, row in df.tail(request.pagination.limit or 500).iterrows():
                points.append(lsi_pb2.LSIHistoryPoint(date=str(row.get("date", "")), lsi=float(row.get("LSI", 0.0)), status=_status(row.get("status", "green")), confidence=float(row.get("confidence", 0.0))))
        return lsi_pb2.GetLSIHistoryResponse(points=points)

    def GetModuleSignals(self, request, context):
        import pandas as pd
        code = MODULE_CODE.get(int(request.module_id), "M1").lower()
        path = ROOT.parents[0] / "data" / "processed" / "dashboard" / f"{code}_dashboard.csv"
        signals = []
        if path.exists():
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                for col, value in row.items():
                    if col in {"date", "source_date", "status"}:
                        continue
                    try:
                        numeric = float(value)
                    except Exception:
                        continue
                    signals.append(modules_pb2.ModuleSignal(date=str(row.get("date", "")), module_id=request.module_id, signal_name=str(col), raw_value=numeric, mad_score=numeric if "MAD_score" in col else 0.0, flag=bool(numeric) if "Flag" in col else False, unit=""))
        return modules_pb2.GetModuleSignalsResponse(module_id=request.module_id, signals=signals, active_flags=[])

    def GetAllModulesSnapshot(self, request, context):
        from pipeline.latest_snapshot import build_latest_snapshot
        snap = build_latest_snapshot()
        modules = []
        for n in range(1, 6):
            code = MODULE_CODE[n]
            signals = []
            for key, value in snap.items():
                if key.startswith(code + "_") and key not in {f"{code}_date", f"{code}_status"}:
                    try:
                        numeric = float(value)
                    except Exception:
                        numeric = 1.0 if bool(value) else 0.0
                    signals.append(modules_pb2.ModuleSignal(date=snap.get(f"{code}_date") or snap["date"], module_id=n, signal_name=key[3:], raw_value=numeric, mad_score=numeric if "MAD_score" in key else 0.0, flag=bool(numeric) if "Flag" in key else False, unit=""))
            modules.append(modules_pb2.ModuleSnapshot(module_id=n, module_name=code, module_score=0.0, signals=signals, active_flags=[]))
        return modules_pb2.GetAllModulesSnapshotResponse(date=snap["date"], modules=modules)


def serve() -> None:
    if IMPORT_ERROR is not None:
        raise RuntimeError(f"Python protobuf stubs are not generated or importable: {IMPORT_ERROR}")
    settings = Settings()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    liquidity_pb2_grpc.add_LiquidityServiceServicer_to_server(LiquidityServicer(), server)
    server.add_insecure_port(f"[::]:{settings.ml_grpc_port}")
    server.start()
    logger.info("Starting gRPC ML service on port %s", settings.ml_grpc_port)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
