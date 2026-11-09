# 11 — 风险、数据来源与著作物管理（v0.1）

## 现实性与伦理

- 本系统所有灾害事件、人数、库存、道路损坏均为**架空模拟数据**。
- 不提供现实救灾或交通安全建议；UI 明确标注 `SIMULATED DATA`。
- 不以排行榜成绩证明某策略在真实灾害中更有效。
- 不把真实灾民个人数据、位置信息或不明授权数据引入赛场。

## 地图与数据

- 初版建议以**自建虚构节点与道路**绘制 2D 场景，保证数据权属清晰。
- Google Maps 若作为显示层，需审查 Maps Platform 最新使用条款、API Key 的 HTTP referrer 限制与调用费用。
- 禁止从 Google Maps 瓦片/导航结果描摹、抓取或导出成自有道路数据库。
- 如未来引入开放道路数据，先核对其具体许可、署名要求和与显示层组合的合规性。

## Bot 输入与服务器安全

- 内置 Bot 与无代码 Bot 优先；不提供任意代码执行环境。
- 外部 HTTPS Bot 未经安全审核不得公开接入，必须防 SSRF、超时、超大响应和非 JSON 内容。
- 实施最小权限，服务器只把**需要的观察数据**发给 Bot。
- 保存外部调用记录以便查错；防滥用机制和数据保留期限需另行确认。

## Google Cloud 成本

- Cloud Run、Firebase、Firestore、Google Maps、Vertex AI/Gemini 的免费额度和计费口径各自不同，不能假定赛事赠金自动覆盖所有 API。
- 设置预算告警、并发上限与 API 配额；预算告警**不会保证自动阻止扣费**。
- 不在前端直接暴露需要保密的 Google Cloud 凭据。

## 提交著作物使用清单

使用比赛官方模板。至少登记：

| 类型 | 例子 | 需要记录 |
| --- | --- | --- |
| 第三方库 | Flask、React、NetworkX（若使用） | 名称、版本、许可、来源 URL |
| 图标/插画 | 自绘或授权图标 | 作者、授权、使用范围 |
| 地图 | Google Maps（若使用） | 服务、官方条款、必要署名 |
| 数据集 | 虚构自建场景、外部公开数据（若使用） | 来源、生成方法、许可、使用目的 |
| AI 生成物 | Gemini 生成的说明或文案（若使用） | 使用位置、人工审核方法 |

## 参考官方文档

- [Google Cloud Run Python/Flask](https://docs.cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service)
- [Firebase Hosting](https://firebase.google.com/docs/hosting/)
- [Google Maps JS 数据层](https://developers.google.com/maps/documentation/javascript/datalayer)
- [Google Maps Platform Terms](https://cloud.google.com/maps-platform/terms)
