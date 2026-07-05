from fastapi import FastAPI

app = FastAPI(title="LionsForge AI", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/ready")
def ready():
    return {"status": "ready"}
