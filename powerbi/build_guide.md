# Power BI 构建说明

## 导入

导入 `data/processed/powerbi/` 下三个 CSV：

- `carrier_kpis.csv`
- `route_risk.csv`
- `buffer_scenarios.csv`

表名分别设为 `Carrier KPI`、`Route Risk`、`Buffer Scenario`。缓冲表无需与其他表建立关系，作为情景选择表使用。

## 页面一：运营健康度

- 卡片：Scheduled Flights、Weighted Completion Rate、Weighted OTP15、Weighted Cancellation Rate。
- 条形图：按航司比较 OTP15，按计划航班量降序。
- 散点图：横轴取消率、纵轴严重延误率、气泡大小为计划航班数。

## 页面二：延误传播风险

- 表格：航线、计划航班、延误率、传播率、吸收率、风险评分。
- 条形图：风险评分最高的15条航线。
- 散点图：传播率与吸收率；气泡大小为有效轮转对。

## 页面三：缓冲情景

- 切片器：Buffer Scenario[buffer_minutes]，设为单选。
- 卡片：Potentially Covered Departures、Relative Reduction。
- 折线图：缓冲分钟与模拟延误起飞数。
- 表格：新增计划分钟和每1000新增分钟覆盖航班数。

项目仓库不提交 `.pbix` 二进制文件时，应保留本说明、DAX文件和刷新所需CSV，确保招聘方可以复核模型与口径。

