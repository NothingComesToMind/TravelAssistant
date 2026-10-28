import asyncio

from fastapi.testclient import TestClient

from travel_app.graph import NoPlacesError, create_graph
from travel_app.schemas import TripRequest


class FakeGateway:
    def __init__(self, *, no_places=False, weather_error=False, route_error=False):
        self.no_places = no_places
        self.weather_error = weather_error
        self.route_error = route_error
        self.calls = []

    async def call(self, name, arguments):
        self.calls.append((name, arguments))
        if name == "search_pois":
            if arguments["category"] == "hotel":
                return {"pois": [{"id": "hotel-1", "name": "真实候选酒店", "location": "118.80,32.06"}]}
            return {"pois": [] if self.no_places else [
                {"id": "poi-1", "name": "候选景点一", "location": "118.79,32.06"},
                {"id": "poi-2", "name": "候选景点二", "location": "118.81,32.07"},
            ]}
        if name == "get_weather":
            if self.weather_error:
                raise TimeoutError("timeout")
            return {"forecasts": []}
        if name == "plan_route":
            if self.route_error:
                raise TimeoutError("timeout")
            return {"polyline": [[118.79, 32.06], [118.81, 32.07]], "distance_m": 1800, "duration_s": 1200}
        raise AssertionError(name)


class InventingPlanner:
    async def plan(self, request, attractions, hotels, forecasts):
        return {"days": [{"poi_ids": ["invented-id", "poi-1", "poi-2"], "hotel_id": "invented-hotel"}]}, None


def test_invalid_poi_and_hotel_ids_are_not_returned():
    gateway = FakeGateway()
    state = asyncio.run(create_graph(gateway, InventingPlanner()).ainvoke({"request": TripRequest(destination="南京", days=1), "warnings": []}))
    day = state["result"].days[0]
    assert [place.id for place in day.attractions] == ["poi-1", "poi-2"]
    assert day.hotel is None
    assert day.routes[0].status == "available"
    assert any("无效" in warning for warning in state["result"].warnings)
    assert all(place.name != "invented-id" for place in day.attractions)


def test_empty_poi_pool_never_generates_a_trip():
    try:
        asyncio.run(create_graph(FakeGateway(no_places=True)).ainvoke({"request": TripRequest(destination="南京", days=1), "warnings": []}))
    except NoPlacesError as exc:
        assert not exc.unavailable
    else:
        raise AssertionError("expected NoPlacesError")


def test_weather_and_route_fail_independently():
    gateway = FakeGateway(weather_error=True, route_error=True)
    state = asyncio.run(create_graph(gateway).ainvoke({"request": TripRequest(destination="南京", days=1), "warnings": []}))
    result = state["result"]
    assert result.days[0].weather is None
    assert result.days[0].routes[0].status == "unavailable"
    assert any("天气查询" in warning for warning in result.warnings)
    assert any("路线查询失败" in warning for warning in result.warnings)


def test_api_returns_422_for_no_places(monkeypatch):
    from travel_app import main

    monkeypatch.setattr(main, "graph", create_graph(FakeGateway(no_places=True)))
    client = TestClient(main.app)
    response = client.post("/api/plan", json={"destination": "南京", "days": 2, "preferences": ""})
    assert response.status_code == 422
    assert "没有找到有效景点" in response.json()["detail"]

