from fastapi import FastAPI

app = FastAPI(title="Phishing Detector API")

@app.get("/health")
def health_check() -> dict[str,  str]:
    return {"status": "ok"}
