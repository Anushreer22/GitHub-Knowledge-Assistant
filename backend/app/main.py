import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("github-knowledge-assistant")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("GitHub Knowledge Assistant API started successfully.")
    yield
    logger.info("GitHub Knowledge Assistant API shutting down.")


app = FastAPI(
    title="GitHub Knowledge Assistant API",
    description="Evidence-Grounded Question Answering on GitHub Repositories using Hybrid Retrieval & Custom Code Embeddings",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)
