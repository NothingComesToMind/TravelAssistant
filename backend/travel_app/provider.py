"""External location data, isolated behind three MCP tools."""

from typing import Any

import httpx

from .config import settings
from .demo_data import DEMO_ATTRACTIONS, DEMO_HOTELS, demo_forecasts


class ProviderError(RuntimeError):
    pass


def _coordinates(value: str) -> list[float]:
    longitude, latitude = (float(part) for part in value.split(",", 1))
    if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
        raise ValueError("coordinate outside valid range")
    return [longitude, latitude]


class TravelProvider:
    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not settings.amap_web_key:
            raise ProviderError("AMAP_WEB_KEY 未配置")
        params = {**params, "key": settings.amap_web_key}
        try:
            async with httpx.AsyncClient(base_url="https://restapi.amap.com", timeout=settings.tool_timeout_seconds) as client:
                response = await client.get(path, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise TimeoutError("地图服务请求超时") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError("地图服务请求失败") from exc
        if str(data.get("status")) != "1":
            raise ProviderError(f"地图服务错误：{data.get('info', '未知错误')}")
        return data

    async def search_pois(self, city: str, category: str, limit: int = 15, keyword: str = "") -> dict[str, Any]:
        if category not in {"attraction", "hotel"}:
            raise ValueError("category must be attraction or hotel")
        if settings.demo_mode:
            # Fixtures intentionally cover one city only; never silently reuse them elsewhere.
            pois = (DEMO_ATTRACTIONS if category == "attraction" else DEMO_HOTELS) if city in {"南京", "南京市"} else []
            return {"pois": pois[:limit], "source": "demo"}

        keyword = keyword[:80].strip() or ("景点" if category == "attraction" else "酒店")
        data = await self._get(
            "/v5/place/text",
            {"keywords": keyword, "region": city, "city_limit": "true", "page_size": min(max(limit, 1), 25)},
        )
        pois = []
        for item in data.get("pois") or []:
            try:
                _coordinates(item["location"])
                if item.get("id") and item.get("name"):
                    address = item.get("address") or ""
                    if isinstance(address, list):
                        address = " ".join(str(part) for part in address)
                    pois.append({"id": item["id"], "name": item["name"], "location": item["location"], "address": str(address)})
            except (KeyError, TypeError, ValueError):
                continue
        return {"pois": pois, "source": "amap"}

    async def get_weather(self, city: str) -> dict[str, Any]:
        if settings.demo_mode:
            return {"forecasts": demo_forecasts(), "source": "demo"}
        districts = await self._get(
            "/v3/config/district",
            {"keywords": city, "subdistrict": 0, "extensions": "base"},
        )
        matches = districts.get("districts") or []
        if not matches or not matches[0].get("adcode"):
            return {"forecasts": [], "source": "amap"}
        weather = await self._get(
            "/v3/weather/weatherInfo",
            {"city": matches[0]["adcode"], "extensions": "all"},
        )
        items = (weather.get("forecasts") or [{}])[0].get("casts") or []
        return {
            "forecasts": [
                {
                    "date": item.get("date", ""),
                    "day_weather": item.get("dayweather", ""),
                    "night_weather": item.get("nightweather", ""),
                    "day_temp": item.get("daytemp", ""),
                    "night_temp": item.get("nighttemp", ""),
                }
                for item in items
                if item.get("date")
            ],
            "source": "amap",
        }

    async def plan_route(self, origin: str, destination: str) -> dict[str, Any]:
        start = _coordinates(origin)
        end = _coordinates(destination)
        if settings.demo_mode:
            return {"distance_m": None, "duration_s": None, "polyline": [start, end], "source": "demo"}

        data = await self._get(
            "/v5/direction/walking",
            {"origin": origin, "destination": destination, "show_fields": "polyline"},
        )
        paths = (data.get("route") or {}).get("paths") or []
        if not paths:
            raise ProviderError("未查询到步行路线")
        path = paths[0]
        points: list[list[float]] = []
        for step in path.get("steps") or []:
            for point in (step.get("polyline") or "").split(";"):
                if point:
                    try:
                        coordinates = _coordinates(point)
                        if not points or points[-1] != coordinates:
                            points.append(coordinates)
                    except ValueError:
                        continue
        if len(points) < 2:
            raise ProviderError("路线没有可绘制的坐标")
        return {
            "distance_m": int(float(path.get("distance") or 0)),
            "duration_s": int(float(path.get("duration") or 0)),
            "polyline": points,
            "source": "amap",
        }

