"""Clearly synthetic fixtures: never presented as verified live POIs/routes."""

from datetime import date, timedelta


DEMO_ATTRACTIONS = [
    {"id": "demo-poi-1", "name": "演示景点 A", "location": "118.79688,32.06025", "address": "演示数据"},
    {"id": "demo-poi-2", "name": "演示景点 B", "location": "118.82617,32.06496", "address": "演示数据"},
    {"id": "demo-poi-3", "name": "演示景点 C", "location": "118.78990,32.08910", "address": "演示数据"},
    {"id": "demo-poi-4", "name": "演示景点 D", "location": "118.75580,32.06770", "address": "演示数据"},
    {"id": "demo-poi-5", "name": "演示景点 E", "location": "118.81410,32.02580", "address": "演示数据"},
]

DEMO_HOTELS = [
    {"id": "demo-hotel-1", "name": "演示住宿 A", "location": "118.79620,32.06080", "address": "演示数据"},
    {"id": "demo-hotel-2", "name": "演示住宿 B", "location": "118.82010,32.05880", "address": "演示数据"},
]


def demo_forecasts() -> list[dict[str, str]]:
    labels = ["晴", "多云", "小雨", "多云", "晴", "晴", "多云"]
    return [
        {
            "date": (date.today() + timedelta(days=index)).isoformat(),
            "day_weather": label,
            "night_weather": label,
            "day_temp": str(22 + index % 3),
            "night_temp": str(15 + index % 2),
        }
        for index, label in enumerate(labels)
    ]

