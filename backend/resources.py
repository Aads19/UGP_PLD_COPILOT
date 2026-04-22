from backend.app.core.config import get_settings
from backend.app.services.pipeline_service import PipelineService, get_pipeline_service


def warmup_resources() -> None:
    get_pipeline_service().warmup()


def get_pipeline() -> PipelineService:
    return get_pipeline_service()


__all__ = ["get_settings", "get_pipeline", "warmup_resources"]
