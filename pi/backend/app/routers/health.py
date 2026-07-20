from fastapi import APIRouter

from ..schemas import HealthResponse
from ..version_info import get_app_version, get_build_time

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=get_app_version(),
        build_time=get_build_time(),
    )
