# 06 — 架构与 Google 技术使用（v0.1）

## 模块结构

```text
Browser (Scene / Bot builder / Replay / Leaderboard)
        │
        ▼
Firebase Hosting (Static assets; optional /api rewrite)
        │
        ▼
Cloud Run — Flask API
   ├── Simulation Engine (pure deterministic Python)
   ├── Bot Adapter (preset / no-code / approved HTTPS)
   ├── Action Validator & Match Runner
   ├── Scoring & Replay Recorder
   └── Persistence Adapter ──► Firestore (optional)

Optional client-only map display: Google Maps JavaScript API
Optional AI assistance: Gemini via server-side Vertex AI path
```

## 设计原则

- **引擎与地图分离**：引擎只认节点、道路和整数回合，不认 Google Maps 路线规划结果。
- **模型与展示分离**：前端接收比赛事件、车辆位置和分数，通过二维图或地图 API 渲染。
- **调度与评分分离**：裁判必须掌握真实状态；Bot 只能获得过滤后的观察值。
- **外部依赖可关停**：无 Maps、Gemini、Firestore 时，仍可运行完整 P0 比赛。
- **Google 技术有实际职责**：Cloud Run 运行核心引擎；Firebase Hosting 提供产品访问；不要只在幻灯片堆砌服务图标。

## 服务选择与理由

| 技术 | 采用理由 | 依赖风险 |
| --- | --- | --- |
| Cloud Run | 容器化 Python Flask API，易部署，满足指定运行平台 | 费用、超时、扩缩容及冷启动 |
| Firebase Hosting | 便于快速部署 SPA 与静态资源，满足指定运行平台 | rewrites / 跨域配置 |
| Firestore（P1） | 保存用户 Bot 配置、成绩、回放索引 | 免费额度和计费，数据结构尚需设计 |
| Google Maps（P1） | 提升灾区场景的可读性，绘制自定义标记/线段 | API Key 限制、计费、素材许可及误导风险 |
| Gemini（P1） | 自然语言设置 Bot 与解释已经发生的行动 | 幻觉、费用、延迟；不得参与裁判评分 |

## 初版地图策略

- **默认：纯虚构节点坐标 + 自绘 2D 路网**，最稳定。
- Maps 作为可选可视化，不依赖 Maps 的 Routes API 处理虚拟封路，也不抓取 Google Maps 的道路内容来构建路网。
- 若后续使用真实路网，需要独立有许可的数据源、合理署名、数据兼容性与条款复核。
- 虚构事件（道路损坏/灾民数量）必须显著显示 `SIMULATED DATA / 架空シミュレーション`。

## 部署及秘密管理

- 本地开发使用 `.env`，不提交；生产凭据只在云端环境/秘密管理中配置。
- Google Maps browser key 限制 HTTP referrer；服务器 API Key 不得暴露给浏览器。
- 开启账单预算告警，限制并发及外部 API 使用；不要依赖预算告警自动停机。
- 提交前通过公开 URL、无缓存、匿名浏览器验证演示路径。

## 参考资料

- [Cloud Run — Python/Flask](https://docs.cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service)
- [Firebase Hosting](https://firebase.google.com/docs/hosting/)
- [Google Maps JS Data Layer](https://developers.google.com/maps/documentation/javascript/datalayer)
- [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output)

以上技术说明为拟定选型，使用前以 Google 最新定价、配额、区域和服务条款为准。


## 当前本地开发实现（v0.3）

浏览器加载 `web/index.html`、`web/style.css`、`web/app.js`，由 `python3 -m reliefroute.server` 的标准库 HTTP 服务提供。同源 `/api/match` 调用既有 Python 引擎，`/api/compare` 运行固定六场对照。无外部字体/地图请求，无 Node 构建步骤，无前端重新计分。服务仅监听回环地址，不能直接当作生产部署。上方 Cloud Run/Flask + Firebase 架构仍是后续部署目标。
