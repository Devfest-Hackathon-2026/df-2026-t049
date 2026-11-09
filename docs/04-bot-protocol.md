# 04 — Bot 决策协议（v0.1 草案）

## 目标

无代码规则 Bot、平台参考 Bot 和开发者代码 Bot 使用同一接口：`decide(observation) -> action`。裁判对所有行动进行相同的校验。**这是规范草案，尚无线上可用端点。**

## 预定 HTTP 协议（P1 外部 Bot）

- 方式：平台以 `POST /decide` 调用经审核的参赛者 HTTPS 服务。
- Header：`Content-Type: application/json`；认证方式待定。
- 运行限制（拟）：2 秒响应超时、32 KB 最大响应体、每回合 1 次调用；失败按 `wait` 处理并记录。
- v0.1 不接受用户直接上传并运行的 Python/JS/C++ 代码。
- 首期仅允许**平台管理员手动审核**并登记的外部地址，不开放任意 URL 自助填入。

## 请求示例（简化）

```json
{
  "protocol_version": "0.1",
  "match_id": "match-public-001",
  "scenario_version": "0.1",
  "turn": 4,
  "total_turns": 24,
  "observation": {
    "depot": { "id": "D1", "node_id": "N0", "stock": 48 },
    "vehicles": [
      { "id": "V1", "status": "idle", "capacity": 10, "node_id": "N0" },
      { "id": "V2", "status": "delivering", "capacity": 10, "node_id": "N3" }
    ],
    "shelters": [
      { "id": "S1", "node_id": "N5", "priority": 3, "outstanding": 20 },
      { "id": "S2", "node_id": "N7", "priority": 1, "outstanding": 8 }
    ],
    "roads": [
      { "id": "R1", "from": "N0", "to": "N5", "travel_turns": 4, "is_open": true },
      { "id": "R2", "from": "N0", "to": "N7", "travel_turns": 2, "is_open": false }
    ]
  }
}
```

完整接口要提供当前**全部必要的路网与需求信息**，示例只含部分节点，不能直接当成可计算的完整场景。请求中禁止提供未来事件计划或私有评测答案。

## 响应示例

```json
{
  "protocol_version": "0.1",
  "actions": [
    { "vehicle_id": "V1", "type": "dispatch", "target_shelter_id": "S1", "quantity": 10 }
  ]
}
```

每辆车每回合最多一个行动；未提及的车视为 `wait`。当前仅定义 `dispatch` 和隐式 `wait`。

## 裁判必须验证

- 协议版本有效；JSON 类型正确；字段完整；数量为正整数。
- 车辆存在，且当前在仓库处于 `idle`；同回合未重复派遣。
- `quantity <= capacity` 且 `quantity <= depot.stock`；不可超发。
- 目标避难所存在、有效，可从当前道路图中到达。
- 不允许 Bot 提交位置、事件、得分等后台字段。
- 返回无效、超时、抛错、无法抵达时不应使整场比赛崩溃；记录拒绝原因并继续。

## 规则型 Bot 的同协议实现

问卷选项写成配置：

```json
{
  "priority_rule": "urgent_first",
  "road_rule": "avoid_congestion",
  "supply_rule": "balanced",
  "risk_level": "medium"
}
```

内部适配器将配置转换为 `decide(observation)`，返回与代码 Bot 完全相同的 `actions` JSON。

Gemini **不是执行该规则引擎的必要依赖**；自然语言配置可作为 P1 功能：Gemini 将自然语言转成上面限定枚举的 JSON，程序严格校验后交给用户确认。

## 外部 Bot 安全（上线前必做）

- 不可直接对用户输入的任意 URL 发起服务器请求（SSRF 风险）。
- 仅允许 HTTPS，检查实际解析目标不含私网、回环和云元数据地址；关闭跳转，对 DNS 重绑定、超时、大小、并发做防护。
- 使用平台 egress 隔离、限流、审计日志和密钥验证；未完成这些措施前不开放公开注册。
- Bot 返回内容视为不可信，不作为 HTML 注入 UI。

## 不要求

Bot 不需要使用 Gemini 或任何特定 LLM，也没有要求用 Python；只需满足约定的 JSON 协议即可。


## 本地 CLI 已实现契约

`0.1-cli` 内置 Bot 接收上面的请求信封；响应在示例基础上**必须增加当前回合 `turn`**：

```json
{"protocol_version":"0.1","turn":4,"actions":[{"vehicle_id":"V1","type":"dispatch","target_shelter_id":"S1","quantity":10}]}
```

请求中的车辆还包含 `cargo`、`target`、`leg`（delivering/returning/null）和 `edge`（road_id/to/remaining 或 null）；在道路中时 `node_id` 表示最后离开的节点。全部道路为无向道路，`travel_turns` 为正整数。避难所包含当前可见需求批次、截止回合、已收/准时收到数量及 `outstanding`。

顶层仅允许 protocol_version/turn/actions，行动仅允许示例中的四个字段。响应回合必须与当前请求一致，动作列表长度不得大于车辆数；信封错误整轮拒绝，单个动作错误则记录原因并继续后续动作。合法格式的同车请求只处理首次出现的一项。未给出的行动为 wait。此实现仅适用于可信内置 Bot；HTTP 接口和执行超时限制仍未实现。


## v0.2 事件与策略补充

`observation.events` 为截至当前回合已发生事件的副本，字段为 id/turn/type/phase/payload；不提供私有计划或道路恢复时刻。道路 `travel_turns` 表示当前进入路段需要的整数耗时，已在路段中的车使用 `edge.remaining`。需求增加只有在发生时才进入 batches/outstanding。最近优先和紧急度优先使用同一个请求/响应信封；协议版本保持 0.1，场景版本区分 0.2-fixture 与 0.2-events。

本地请求的 match_id 固定为 `local-match`，不把生成 seed 编码进 Bot 可见标识。seed 仅保留在最终开发者记录中；未来服务端应分配与 seed 无关的比赛 ID。
