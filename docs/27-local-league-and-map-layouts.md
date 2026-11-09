# 本地联赛启动与三种视觉布局

## 已复现的错误

8000 端口 /health 返回 200，/api/league 返回 503 和 Hourly league has not been enabled on this server。只启动 reliefroute.server 不会自动启用联赛；并非数据库损坏。环境变量只属于启动服务的进程，重开终端不能继承此前临时设置。

## 推荐启动（PowerShell，仓库根目录）

```powershell
Set-Location 'C:\DevFest GDGoC Japan Hackathon 2026'
python scripts/local_league.py --demo --port 8016
```

打开 http://127.0.0.1:8016/ 和 http://127.0.0.1:8016/league 。默认数据库固定在 outputs/local-league.sqlite3，已被 Git 忽略；重启使用同一文件。脚本清除本进程的云 bucket 配置，只访问本地 SQLite，不改变其他进程或线上联赛。

--demo 仅在没有 Bot 时注册两个明确命名 Local demo 的参考 Bot，以前一小时注册时间作为演示夹具，调用现有引擎结算当前小时。并非正式即时开赛规则。重复启动不重复创建 Bot，同小时已结算不会再次计分。

仅初始化空联赛：`python scripts/local_league.py --db outputs/empty-league.sqlite3 --port 8017`。

网页创建自己的 Bot 后须等待下一小时；在另一个终端执行：

```powershell
python scripts/local_league.py --once
```

此命令只结算当前小时，不提前下一小时、不重算已结算轮次。持续本地自动结算可另开终端运行 `python -m reliefroute.league --db outputs/local-league.sqlite3`。关闭终端后 worker 停止，公开云端自动赛由队友管理的 Scheduler 负责。

流程为创建 → 部署并保存令牌 → 下一小时参赛 → 排行榜 → 最新结果观战。不能将新注册 Bot 未立即出现在结果中视作故障。

## 地图变化

城市：设施按规整矩形布局，道路正交折线；沿河：设施两岸分布，河流贯穿中央，桥栏只绘制在实际道路跨越河带的部分；山区：设施沿斜向山谷错落分布，曲线路面、树林和等高线。

节点绘制位置、道路形状只是表示层，不修改 from/to、travel_turns、库存、Bot 或评分。视觉道路交叉不是新增可转弯路口。车辆与道路使用同一几何路径。

真实三套地理路网仍需要后端 map ID、节点坐标、道路几何、运输耗时和真实灾害原因；目前不能宣称桥梁损坏、洪水或滑坡机制已实现。

## 验证

Python 59 项；原有几何 9504 案例（已改为使用三套实际坐标）；联赛几何 1440 案例；时钟、语言、复制处理器测试均通过。浏览器已检查沿河和山区布局、三语导航中的日语显示、本地排行榜两 Bot 与回放 47/47，未捕获 JS 错误。未对每种布局在所有屏幕尺寸做穷尽检查。
