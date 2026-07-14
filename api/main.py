from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.los import router as los_router
from api.routers.discharge import router as discharge_router
from api.routers.ed_forecast import router as ed_router
from api.routers.bed_forecast import router as bed_router
from api.routers.hospital_state import router as hospital_state_router
from ui.ui_router import router as ui_router

app = FastAPI(title="AI Hospital Prototype API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(los_router)
app.include_router(discharge_router)
app.include_router(ed_router)
app.include_router(bed_router)
app.include_router(hospital_state_router)
app.include_router(ui_router, prefix="/ui")

@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "ai-hospital-prototype"}
