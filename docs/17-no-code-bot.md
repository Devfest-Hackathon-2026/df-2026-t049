# 无代码 Bot v1.0

选择“我的策略”，设置三个参数后运行。对照赛比较当前配置和两个固定基线在公开 seed 11/22/33 上的九场比赛。浏览器保存该次对照结果中的配置，点击历史结果时恢复当时参数，而不是悄悄改用新设置。

| 参数 | 选项 | 确定性行为 |
| --- | --- | --- |
| priority_rule | urgency / nearest / fair | 剩余时间最少 / 最短耗时 / 已配送及在途预留后的覆盖率最低 |
| load_rule | full / half | 单车装载上限为车辆容量 / 容量的一半向下取整且至少为 1 |
| dispatch_rule | any / full_load | 有可配送物资即出发 / 库存与目标未预留需求足够达到装载上限才出发 |

装载上限不是强制超额装货。`any` 总是取库存、上限、未预留需求三者最小值。`full_load` 过滤无法达到上限的目标，可能导致剩余小批需求一直未送达；这是一项可观察的策略取舍。

公平优先使用精确有理数比较当前覆盖率；依次以距离、避难所 ID 打破平局。同轮依车辆 ID 顺序预留物资，计入已有在途物资，避免多车重复争抢同一需求。未知未来需求不进入决策。

引擎仍决定最短耗时路线；表单不会宣称提供当前不支持的自定义道路规则。所有策略走相同 `observation -> action -> dispatch` 裁判，没有增加事件或资源类型。

## API 与复现

```text
GET /api/match?scenario=events&seed=22&bot=custom&priority_rule=fair&load_rule=full&dispatch_rule=any
GET /api/compare?priority_rule=fair&load_rule=full&dispatch_rule=any
```

三个字段必须齐全且为规定枚举。非 custom Bot 不接受配置字段；未知/重复字段返回 400。旧的无参数 `/api/compare` 仍返回原六场基线。

完整记录增加 `bot_config` 和 `bot_version: "1.0"`；它们不是未来事件，也不改变评分版本。记录不自动上传或持久化。刷新页面后需要重新配置；请下载 JSON 留存实验结果。

```bash
python -m reliefroute --scenario events --seed 22 --bot custom --config examples/fair-strategy.json --output outputs/custom.json
python -m reliefroute --rescore outputs/custom.json
python -m reliefroute --compare --config examples/fair-strategy.json --output outputs/custom-comparison.json
```

`--rescore` 重算已有记录的分数，不执行配置。若要重跑，使用记录中的 seed、scenario 对应类型和 bot_config。只支持当前版本，不承诺未来规则升级后的逐字节相同。

## 开发验收基线

公平优先/全部容量/立即派车的三 seed 分数为 76.898148、73.506944、73.333333，均分 74.579475。最近优先均分 73.506944、紧急度优先均分 78.350051 保持不变。

这三个公开样例不能证明策略的一般优劣。seed 22、33 中，紧急度优先的加权覆盖率更高，但最低避难所覆盖率为 0.5；公平配置保持 0.75。演示时应同时展示分项与回放，而不是只宣称“总分更高就是更好”。
