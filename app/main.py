import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import init_db
from app.routers import frontend, cart, admin, seo

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Инициализация БД...")
    await init_db()
    logger.info("БД готова")

    # Запуск планировщика парсинга
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from app.services.parser import run_parser

        cron_expr = settings.PARSER_CRON.split()
        if len(cron_expr) == 5:
            minute, hour, day, month, day_of_week = cron_expr
            scheduler = AsyncIOScheduler()
            scheduler.add_job(
                run_parser, CronTrigger(
                    minute=minute, hour=hour, day=day,
                    month=month, day_of_week=day_of_week
                ),
                id="parser", replace_existing=True
            )
            scheduler.start()
            app.state.scheduler = scheduler
            logger.info(f"Планировщик парсинга запущен: {settings.PARSER_CRON}")
    except Exception as e:
        logger.warning(f"Планировщик не запущен: {e}")

    yield

    # Shutdown
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.SITE_NAME,
    docs_url=None,  # Скрываем в production
    redoc_url=None,
    lifespan=lifespan,
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Routers
app.include_router(seo.router)
app.include_router(frontend.router)
app.include_router(cart.router)
app.include_router(admin.router)


# 404 handler
@app.exception_handler(404)
async def not_found(request: Request, exc):
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="app/templates")
    return templates.TemplateResponse(
        "404.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
            "site_phone": settings.SITE_PHONE,
        },
        status_code=404,
    )
