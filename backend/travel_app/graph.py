"""Parallel specialist agents -> planning agent -> POI validation and routes."""

import asyncio
import operator
from datetime import date, timedelta
from typing import Annotated, Any, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph

from .config import settings
from .planner import PlanningAgent, deterministic_draft
from .schemas import DayPlan, Place, RouteSegment, TripPlan, TripRequest, Weather


class ToolGateway(Protocol):
    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...


class NoPlacesError(RuntimeError):
    def __init__(self, message: str, unavailable: bool = False):
        super().__init__(message)
        self.unavailable = unavailable


class PlanState(TypedDict, total=False):
    request: TripRequest
    attractions: list[Place]
    hotels: list[Place]
    forecasts: list[Weather]
    search_unavailable: bool
    draft: dict[str, Any]
    result: TripPlan
    warnings: Annotated[list[str], operator.add]


def _parse_places(payload: dict[str, Any]) -> list[Place]:
    places: list[Place] = []
    seen: set[str] = set()
    for item in payload.get("pois") or []:
        try:
            longitude, latitude = (float(part) for part in item["location"].split(",", 1))
            place = Place(id=str(item["id"]), name=item["name"], longitude=longitude, latitude=latitude, address=item.get("address") or "")
            if place.id not in seen:
                places.append(place)
                seen.add(place.id)
        except (KeyError, TypeError, ValueError):
            continue
    return places


def _preference_keyword(preferences: str) -> str:
    for word in ("博物馆", "历史", "古迹", "公园", "自然", "艺术", "美术馆", "科技馆", "寺庙"):
        if word in preferences:
            return "博物馆" if word == "历史" else "风景区" if word == "自然" else word
    return ""


def create_graph(gateway: ToolGateway, planner: PlanningAgent | None = None):
    planning_agent = planner or PlanningAgent()

    async def attraction_agent(state: PlanState) -> dict[str, Any]:
        request = state["request"]
        arguments = {"city": request.destination, "category": "attraction", "limit": 15}
        keyword = _preference_keyword(request.preferences)
        try:
            calls = [gateway.call("search_pois", arguments)]
            if keyword:
                calls.append(gateway.call("search_pois", {**arguments, "keyword": keyword}))
            payloads = await asyncio.gather(*calls, return_exceptions=True)
            places: list[Place] = []
            failed = 0
            for payload in payloads:
                if isinstance(payload, BaseException):
                    failed += 1
                else:
                    places.extend(_parse_places(payload))
            places = list({place.id: place for place in places}.values())
            if failed == len(payloads):
                return {"attractions": [], "search_unavailable": True, "warnings": ["地点搜索服务不可用"]}
            return {"attractions": places, "search_unavailable": False, "warnings": ["部分地点搜索失败，已保留成功结果"] if failed else []}
        except Exception:
            return {"attractions": [], "search_unavailable": True, "warnings": ["地点搜索服务不可用"]}

    async def weather_agent(state: PlanState) -> dict[str, Any]:
        try:
            payload = await gateway.call("get_weather", {"city": state["request"].destination})
            forecasts = [Weather.model_validate(item) for item in payload.get("forecasts") or []]
            return {"forecasts": forecasts, "warnings": [] if forecasts else ["天气查询无结果"]}
        except Exception:
            return {"forecasts": [], "warnings": ["天气查询超时或失败；未展示未经核实的天气"]}

    async def hotel_agent(state: PlanState) -> dict[str, Any]:
        try:
            payload = await gateway.call("search_pois", {"city": state["request"].destination, "category": "hotel", "limit": 10})
            hotels = _parse_places(payload)
            return {"hotels": hotels, "warnings": [] if hotels else ["未查到住宿地点"]}
        except Exception:
            return {"hotels": [], "warnings": ["住宿查询失败；不展示未经核实的住宿建议"]}

    async def planner_agent(state: PlanState) -> dict[str, Any]:
        if not state.get("attractions"):
            raise NoPlacesError(
                "地点搜索失败，无法生成经过验证的行程" if state.get("search_unavailable") else "没有找到有效景点，无法生成行程",
                unavailable=bool(state.get("search_unavailable")),
            )
        draft, warning = await planning_agent.plan(state["request"], state["attractions"], state.get("hotels", []), state.get("forecasts", []))
        return {"draft": draft, "warnings": [warning] if warning else []}

    async def validate_and_route(state: PlanState) -> dict[str, Any]:
        request = state["request"]
        candidate_by_id = {place.id: place for place in state["attractions"]}
        hotel_by_id = {place.id: place for place in state.get("hotels", [])}
        fallback = deterministic_draft(request, state["attractions"], state.get("hotels", []))["days"]
        raw_days = state["draft"].get("days") or []
        dates = [((request.start_date or date.today()) + timedelta(days=index)).isoformat() for index in range(request.days)]
        weather_by_date = {item.date: item for item in state.get("forecasts", [])}
        output_days: list[DayPlan] = []
        warnings: list[str] = []
        for index in range(request.days):
            raw_day = raw_days[index] if index < len(raw_days) and isinstance(raw_days[index], dict) else fallback[index]
            raw_ids = raw_day.get("poi_ids") if isinstance(raw_day.get("poi_ids"), list) else []
            selected_ids: list[str] = []
            for value in raw_ids[:3]:
                if isinstance(value, str) and value in candidate_by_id and value not in selected_ids:
                    selected_ids.append(value)
                else:
                    warnings.append(f"第 {index + 1} 天含无效或重复 POI ID，已移除")
            if not selected_ids:
                selected_ids = fallback[index]["poi_ids"]
                warnings.append(f"第 {index + 1} 天未选中有效景点，改用已检索地点")
            hotel_id = raw_day.get("hotel_id")
            hotel = hotel_by_id.get(hotel_id) if isinstance(hotel_id, str) else None
            if hotel_id and hotel is None:
                warnings.append(f"第 {index + 1} 天住宿 ID 未通过校验，已移除")
            selected = [candidate_by_id[place_id] for place_id in selected_ids]
            segments: list[RouteSegment] = []
            for start, end in zip(selected, selected[1:]):
                try:
                    payload = await gateway.call(
                        "plan_route",
                        {"origin": f"{start.longitude},{start.latitude}", "destination": f"{end.longitude},{end.latitude}"},
                    )
                    polyline = payload.get("polyline") or []
                    if len(polyline) < 2:
                        raise ValueError("route has no drawable polyline")
                    segments.append(RouteSegment(from_id=start.id, to_id=end.id, status="available", distance_m=payload.get("distance_m"), duration_s=payload.get("duration_s"), polyline=polyline))
                except Exception:
                    segments.append(RouteSegment(from_id=start.id, to_id=end.id, status="unavailable"))
                    warnings.append(f"第 {index + 1} 天 {start.name} 至 {end.name} 的路线查询失败")
            if dates[index] not in weather_by_date:
                warnings.append(f"第 {index + 1} 天天气不在可用预报范围内")
            output_days.append(DayPlan(day=index + 1, date=dates[index], attractions=selected, hotel=hotel, weather=weather_by_date.get(dates[index]), routes=segments))
        result = TripPlan(destination=request.destination, days=output_days, warnings=list(dict.fromkeys(state.get("warnings", []) + warnings)), data_mode="demo" if settings.demo_mode else "live")
        return {"result": result, "warnings": warnings}

    graph = StateGraph(PlanState)
    graph.add_node("attraction_agent", attraction_agent)
    graph.add_node("weather_agent", weather_agent)
    graph.add_node("hotel_agent", hotel_agent)
    graph.add_node("planner_agent", planner_agent)
    graph.add_node("validate_and_route", validate_and_route)
    graph.add_edge(START, "attraction_agent")
    graph.add_edge(START, "weather_agent")
    graph.add_edge(START, "hotel_agent")
    graph.add_edge(["attraction_agent", "weather_agent", "hotel_agent"], "planner_agent")
    graph.add_edge("planner_agent", "validate_and_route")
    graph.add_edge("validate_and_route", END)
    return graph.compile()

