# TravelAssistant 智能旅行规划平台


一个可本地运行的 Python + LangGraph + MCP + FastAPI + Vue 旅行规划应用。用户输入目的地、出行天数和偏好后，景点、天气、住宿三个专职节点并行获取信息，规划节点生成每日景点 ID 列表，再由程序进行 ID 校验、坐标回填和路线查询。前端按天展示行程和地图。

## 已实现的流程

```text
Vue 表单 → FastAPI /api/plan → LangGraph
                         ├─ 景点 Agent ─┐
                         ├─ 天气 Agent ─┼─ 规划 Agent → POI ID 校验 → 路线查询 → 响应
                         └─ 住宿 Agent ─┘
                                │
                     MCP Client ↔ 自建 MCP Server ↔ 地图/天气服务
```

- MCP Server 暴露 `search_pois`、`get_weather`、`plan_route` 三个工具。实时模式由服务器端调用高德 Web 服务；密钥只存放在后端 `.env`，不会传给模型或浏览器。
- 规划 Agent 只能从本次检索得到的 POI ID 中挑选。无效 ID 会被移除并用已检索的候选地点补齐；无有效景点时返回错误，不生成虚构行程。
- 地点无结果、地点服务错误、天气查询失败、住宿查询失败、路线查询失败分别处理。路线失败只隐藏该段路线，不伪造道路；天气超出预报范围时明确标注。
- 不配置 API 密钥也能运行演示模式。演示地点及路线都是**虚构样例**，界面会标注“演示数据”，仅支持目的地“南京”；这不是实时数据验证。

## 环境要求

- Python 3.11 或更新版本；Node.js 20 或更新版本。
- 实时模式需要高德 Web 服务 Key，使用模型规划还需要兼容 OpenAI Chat Completions 的模型 Key。高德 Web 服务的可用范围、配额和使用条款以高德官方控制台为准。

## 启动

在 PowerShell 中打开三个终端。以下命令均从 `TravelAssistant` 根目录开始：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

编辑 `backend/.env`：默认 `TRAVEL_DEMO_MODE=true` 无需 Key；实时模式改为 `false` 并填写 `AMAP_WEB_KEY`。如需使用大模型生成行程，再填写 `LLM_API_KEY`、`LLM_BASE_URL` 和 `LLM_MODEL`。没有模型 Key 时，系统只会基于已检索 POI 生成基础行程，并在响应中提示。

终端 1（MCP 工具服务）：

```powershell
cd backend
.\.venv\Scripts\python.exe -m travel_app.mcp_server
```

终端 2（FastAPI）：

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn travel_app.main:app --host 127.0.0.1 --port 8000
```

终端 3（Vue）：

```powershell
cd frontend
npm install
npm run dev
```

打开 `http://127.0.0.1:5173/`。接口文档在 `http://127.0.0.1:8000/docs`。健康检查为 `GET /api/health`。

## 验证

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

测试覆盖并行图的汇总、非法 POI/住宿 ID 拦截、地点为空、天气与路线独立失败，以及通过 MCP 协议发现和调用自建工具。也可在演示模式下向 `POST /api/plan` 发送：

```json
{"destination":"南京","days":3,"preferences":"博物馆、历史文化"}
```

## 实时模式的边界

- 目前地点仅做中国大陆城市的高德搜索；景点和酒店都是 POI 候选，不宣称酒店实时价格、空房或景点营业时间。
- 路线目前采用步行规划；跨城交通、预算精算、订票不在本版范围内。
- 高德天气预报有可用天数限制，超过范围不展示推测天气。
- 前端使用 OpenStreetMap 底图和 Leaflet；展示时将高德 GCJ-02 坐标转换到 WGS84。地图底图需要网络连接，生产部署应遵守底图服务的使用政策。
- 演示模式中的直线仅用于验证页面和接口，不是道路路线。实时模式只绘制地图服务返回的路线坐标。

## 参考文档

- [LangGraph 图工作流](https://docs.langchain.com/oss/python/langgraph/use-graph-api)
- [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/)
- [高德 POI 搜索 2.0](https://developer.amap.com/api/webservice/guide/api/newpoisearch)
- [高德路径规划 2.0](https://developer.amap.com/api/webservice/guide/api/newroute)

