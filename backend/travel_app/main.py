"""FastAPI entry point."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .graph import NoPlacesError, create_graph
from .mcp_gateway import MCPGateway
from .schemas import TripPlan, TripRequest


app = FastAPI(title="TravelAssistant", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["*"])
graph = create_graph(MCPGateway())


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "data_mode": "demo" if settings.demo_mode else "live"}


@app.post("/api/plan", response_model=TripPlan)
async def plan_trip(request: TripRequest) -> TripPlan:
    if not settings.demo_mode and not settings.amap_web_key:
        raise HTTPException(status_code=503, detail="实时模式缺少 AMAP_WEB_KEY")
    try:
        state = await graph.ainvoke({"request": request, "warnings": []})
        return state["result"]
    except NoPlacesError as exc:
        raise HTTPException(status_code=503 if exc.unavailable else 422, detail=str(exc)) from exc

