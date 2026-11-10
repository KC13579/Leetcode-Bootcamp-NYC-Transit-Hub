from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Return the application liveness status without querying external providers."""
    return {"status": "ok"}
