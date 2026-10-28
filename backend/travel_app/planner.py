"""Planning agent: LLM selects IDs, program owns all canonical place fields."""

import json
import re
from typing import Any

import httpx

from .config import settings
from .schemas import Place, TripRequest, Weather


def deterministic_draft(request: TripRequest, attractions: list[Place], hotels: list[Place]) -> dict[str, Any]:
    """Offline and LLM-failure fallback; selects only IDs from retrieved candidates."""
    return {
        "days": [
            {
                "poi_ids": [attractions[(day * 3 + offset) % len(attractions)].id for offset in range(min(3, len(attractions)))],
                "hotel_id": hotels[0].id if hotels else None,
            }
            for day in range(request.days)
        ]
    }


class PlanningAgent:
    async def plan(
        self,
        request: TripRequest,
        attractions: list[Place],
        hotels: list[Place],
        forecasts: list[Weather],
    ) -> tuple[dict[str, Any], str | None]:
        if not settings.llm_api_key or settings.demo_mode:
            return deterministic_draft(request, attractions, hotels), "当前使用演示规划；未调用大模型" if settings.demo_mode else "未配置 LLM，采用已检索地点生成基础行程"

        candidates = {
            "destination": request.destination,
            "days": request.days,
            "preferences": request.preferences,
            "attractions": [{"id": p.id, "name": p.name, "address": p.address} for p in attractions],
            "hotels": [{"id": p.id, "name": p.name} for p in hotels],
            "weather": [w.model_dump() for w in forecasts],
        }
        system = (
            "你是旅行规划 Agent。只从输入的 attractions 和 hotels 中选 ID，不得编造 ID、坐标、价格或开放时间。"
            "按用户偏好安排每日 1 至 3 个景点，允许不同天重复。仅输出 JSON 对象："
            '{"days":[{"poi_ids":["景点ID"],"hotel_id":"酒店ID或null"}]}。'
            "days 数组长度必须等于输入天数。天气可用于调整选择，但不要声称预报范围外的天气。"
        )
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    settings.llm_base_url.rstrip("/") + "/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json={
                        "model": settings.llm_model,
                        "temperature": 0.2,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": json.dumps(candidates, ensure_ascii=False)},
                        ],
                    },
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.I)
            draft = json.loads(cleaned)
            if not isinstance(draft, dict) or not isinstance(draft.get("days"), list):
                raise ValueError("LLM did not return days array")
            return draft, None
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            return deterministic_draft(request, attractions, hotels), "规划模型不可用，已用检索到的地点生成基础行程"

