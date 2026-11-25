from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.errors import register_exception_handlers
from app.core.middleware import configure_logging, install_middleware
from app.core.ratelimit import limiter
from app.routers import auth, public
from app.routers.owner import appointments, hours, services, stats


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="SlotEase API",
        version="1.0.0",
        description="Multi-tenant appointment booking for clinics, salons and physio centres.",
    )
    app.state.limiter = limiter
    register_exception_handlers(app)
    install_middleware(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(public.router)
    app.include_router(appointments.router)
    app.include_router(services.router)
    app.include_router(hours.router)
    app.include_router(stats.router)
    return app


app = create_app()
