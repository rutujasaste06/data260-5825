#server config: CORS + JSON

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router

app = FastAPI(title="Clinical Trial Document API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)  # JSON body parsing is built into FastAPI

@app.get("/")
def root():
    return {"service": "s5825_doc", "status": "ok"}