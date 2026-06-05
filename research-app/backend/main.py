from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import prompts, tasks

app = FastAPI(title="揽宝智能投研 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prompts.router)
app.include_router(tasks.router)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}
