from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from lib.db import engine, init_db
from routers.dashboard import router as dashboard_router


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Startup runs before the yield, shutdown after it. Add your own setup/teardown here.
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await engine.dispose()


# Create the main app without a prefix
app = FastAPI(lifespan=lifespan)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Razorpay AI Financial Copilot API", "status": "ready"}

api_router.include_router(dashboard_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Keep router inclusion last so every endpoint remains under /api.
app.include_router(api_router)
