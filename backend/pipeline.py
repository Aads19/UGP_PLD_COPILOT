from backend.app.core.config import get_settings
from pld_copilot.pipeline import PLDCopilotPipeline


def build_pipeline() -> PLDCopilotPipeline:
    return PLDCopilotPipeline.from_config(get_settings().pipeline_config)


def run_pipeline(query: str):
    return build_pipeline().run(query)


__all__ = ["build_pipeline", "run_pipeline"]
