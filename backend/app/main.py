from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import questions, exams, materials, knowledge, chat, scopes, drafts
from .services.rag import RAGPipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Ensure ChromaDB is initialized
    RAGPipeline()
    yield


app = FastAPI(
    title="DS Exam System API",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(questions.router, prefix="/api")
app.include_router(exams.router, prefix="/api")
app.include_router(materials.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(scopes.router, prefix="/api")
app.include_router(drafts.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
