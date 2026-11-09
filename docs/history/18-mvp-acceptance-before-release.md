# 過去の開発記録（現行仕様・今回の検証結果ではありません）

# MVP 验收记录

2026-11-09 JST；基于 `a026438` 后的 `feature/complete-mvp` 本地工作树。**产品核心与公开 Google 部署已验收；正式提交材料仍待完成。**

| MVP 条件 | 当前证据 | 状态 |
| --- | --- | --- |
| 三个固定公开 seed | 11/22/33；原回归及自定义策略重复运行 | 已验证 |
| 24 回合与物资守恒 | Python 单元测试，含全部 12 种策略组合 | 已验证 |
| 三类事件 | 封路/拥堵/需求增加原有测试通过 | 已验证 |
| 统一 Bot 契约与行动校验 | 两个基线与配置 Bot 共享裁判；非法输入用例 | 已验证 |
| 三个无代码策略参数 | 三语表单、参数行为测试及浏览器运行 | 已验证 |
| 评分可重算 | JSON 往返与 score_record 测试；原基线不变 | 已验证 |
| 比赛展示与回放 | 9504 个几何检查（含全部自定义组合）；浏览器实际比赛/历史配置恢复 | 已验证 |
| 桌面与手机布局 | 1440px 与 390px 检查，页面无水平溢出；地图内允许横向滚动 | 已验证 |
| Google 运行平台公开 URL | Cloud Run revision 00002-hng；外部 smoke PASS 与匿名浏览器核心流程 | 已验证 |
| Linux 生产容器 | 远端 CI 构建并启动 Gunicorn，完整 HTTP 冒烟通过 | 已验证 |
| README / 架构图 / 决策说明 | 仓库文档；正式模板未提供 | 仓库内容已准备/待套模板 |
| 完整演讲视频 | 日语脚本待录制；不能用静态假成绩替代 Demo | 未完成 |
| 著作物清单 | CI 已核对 Python 3.13.18 / Gunicorn 26.2.0；见 22 文档 | 技术来源已整理，待官方模板与团队许可确认 |
| 官方仓库 / Drive / Form | 官方仓库已从主办方邮件核实，本地提交副本已准备；模板与 Form 尚未找到 | 未公开推送、未提交 |

## 本机测试

- Python 3.15.0：`python -m unittest discover -s tests -q`，40 tests OK。
- Node 26.13.0：`node tests/frontend_replay.cjs`，9504 cases / 44 records PASS。
- `node --check web/app.js` 通过。
- `python -m reliefroute --compare --config examples/fair-strategy.json` 输出九场与三策略排名，基线未变。
- 新增策略覆盖 12 组枚举组合 × 3 seed × 3 次重跑，验证日志一致、合法行动、每回合守恒和重算。
- 本机 HTTP 测试需允许访问 loopback；最初 WinError 10013 是运行环境隔离，放行后通过。

## 浏览器实测

2026-11-09，在真实本地 Python 服务上：

1. 选择公平/全部容量/立即派车，运行并打开策略对照；九场结果和均分 74.58 正常。
2. 打开 seed 22 自定义回放；参数恢复、分数 73.51、24 回合正常。
3. 切换日语；修改最近/半载/等满载，分数变为 67.50，初始车辆载货 5。
4. 从旧对照表再次打开 seed 22 自定义结果，恢复公平/全部容量/立即派车，而不是采用刚修改的参数。
5. 中/日/英内容正常，浏览器错误日志为空；390px 表单可操作，1440px 排行可展示。

本地验收时尚未验证云端；后续云端证据见下文。仍未声称完成冷启动专项测试、持续运行到 11/14、官方模板、录屏视频及官方提交。

- CLI 已实际导出 seed 22 的自定义 JSON，并用 `--rescore` 得到完全一致的分数。
- 本机运行中的服务通过 `scripts/smoke.py` 的静态资源、健康检查、自定义比赛及九场对照验证。


## 远端 CI 与生产容器证据

- 代码提交 `69b6316ed49a2045c9ddfaa27408cf89cad8fd9f`；[PR #4](https://github.com/hachimitsuGL/reliefroute-arena/pull/4)。
- [Regression run 42500092759](https://github.com/hachimitsuGL/reliefroute-arena/actions/runs/42500092759) 全部成功：Windows 测试、Ubuntu 测试、Linux 容器。
- 两个平台运行 Python 3.13；40 项测试、9504 个回放检查、55 文件 manifest 全部通过。
- 容器实际运行 Python 3.13.18 / Gunicorn 26.2.0，两个同步 worker，绑定 `0.0.0.0:8080`，非 root 用户。健康/静态页面/自定义比赛/九场对照均通过。
- 初次容器检查遇到刚启动时的连接重置；修复为在就绪阶段重试瞬态网络错误，再次运行成功。没有绕过 API 断言或伪造结果。
- 本节后的文档修订不改变上述代码；当时公开 Cloud Run 验收仍待完成；后续证据见下文。


## 官方提交入口核实（2026-11-09）

- 主办方分配的公开仓库为 [Devfest-Hackathon-2026/df-2026-t049](https://github.com/Devfest-Hackathon-2026/df-2026-t049)，团队 Hachimitsu，线上组。GitHub 连接器确认当前账号有 push 权限。
- [官方仓库初始说明](https://github.com/Devfest-Hackathon-2026/df-2026-t049/blob/main/README.md) 明确不能使用 GitHub Actions/Pages，审查以官方仓库内容为准。因此保留开发仓库 CI，最终向官方仓库移交源码快照。
- 官方仓库已有 MIT LICENSE；开发仓库尚未选定许可。未擅自把本作品改为 MIT 或公开推送。
- 已在独立本地副本准备源码、日语入口说明和源提交 SHA，逐文件验证与开发提交一致，保留官方初始说明及 LICENSE，不移交开发 Git 历史。
- 已找到 11/3 发出的 Cloud Credit 通知邮件，但未读取/复制兑换码，用户尚未激活。
- Drive 的 DevFest/GDG 搜索及主办方邮件中的模板/提交关键词检索未找到正式模板，不能据此断言模板不存在；仍需 Discord 的实际链接。


## 首次 Cloud Run 部署实测

- 用户提供的部署输出显示 revision `reliefroute-arena-00001-6bx` 已接收全部流量。
- 实际匿名访问 https://reliefroute-arena-293373083050.asia-northeast1.run.app/ 返回 200；app.js、i18n.js、style.css 均返回 200。
- 自定义 fair/full/any seed 22 返回 24 回合及 73.506944 分；九场对照均分为 urgency 78.350051、custom 74.579475、nearest 73.506944，与本地基线一致。
- 发现 `/healthz` 被 Google 网关以 HTML 404 拦截；其他功能正常。源码将健康路径改为 `/health`，待用户重新部署并验证新路径。参考 https://docs.cloud.google.com/run/docs/known-issues 。
- 尚未把匿名 API 成功等同于完整浏览器验收、持续可用性或正式材料提交。


## 第二次 Cloud Run 部署与外部验收（2026-11-09 JST）

- 用户输出显示 revision `reliefroute-arena-00002-hng` 已接收 100% 流量；URL：https://reliefroute-arena-293373083050.asia-northeast1.run.app 。
- 云端源码快照由用户应用 `/healthz` → `/health` 修复后部署；开发仓库对应修复提交为 `3426c49082d5cecd302a10a09a0b9ae9911865b3`。未将云端快照冒称为该 Git 提交的完整逐字构建。
- 用户在 Cloud Shell 运行 smoke PASS；随后从外部电脑独立运行同一脚本 PASS：健康、静态资源、自定义比赛、九场比较。
- 匿名浏览器实际选择 fair/full/any、seed 22 并运行：分数 73.51，公平性 75%；打开九场对照，custom 均分 74.58。
- 点击 seed 22 自定义结果，参数正确恢复；时间轴可到 23/23，浏览器错误日志为空。
- 持续运行到 11/14、冷启动专项测试、正式视频与提交尚不属于此次验收结果。主办方额度是否兑换仍未确认，不影响上述已发生的部署事实。
