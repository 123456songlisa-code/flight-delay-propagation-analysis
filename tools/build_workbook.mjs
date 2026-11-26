import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(".");
const payload = JSON.parse(await fs.readFile(path.join(root, "data/processed/workbook_payload.json"), "utf8"));
const outputDir = path.join(root, "outputs");
const previewDir = path.join(outputDir, "previews");
await fs.mkdir(previewDir, { recursive: true });

const wb = Workbook.create();
const dashboard = wb.worksheets.add("运营总览");
const scenarios = wb.worksheets.add("缓冲情景");
const routes = wb.worksheets.add("高风险航线");
const metrics = wb.worksheets.add("指标字典");
const sources = wb.worksheets.add("来源与限制");
const inputs = wb.worksheets.add("数据输入");

const font = "Arial";
const navy = "#16324F";
const blue = "#2F6690";
const lightBlue = "#EAF2F8";
const amber = "#F4B942";
const lightAmber = "#FFF3CD";
const red = "#B42318";
const lightRed = "#FDECEC";
const green = "#2E7D32";
const gray = "#667085";
const lightGray = "#F2F4F7";
const rotationSufficient = payload.summary.quality.rotation_sample_sufficient;
const scheduledFlights = Number(payload.summary.kpis.scheduled_flights || 0);
const validRotations = Number(payload.summary.kpis.valid_rotation_pairs || 0);
const inboundDelayedPairs = Number(payload.summary.kpis.inbound_delayed_pairs || 0);
const scopeLabel = `${payload.summary.scope.date_start} 至 ${payload.summary.scope.date_end}，BTS官方月度数据，${scheduledFlights.toLocaleString("zh-CN")}条计划航班`;
const qualityText = rotationSufficient
  ? `质量检查通过：识别 ${validRotations.toLocaleString("zh-CN")} 个有效轮转对，其中 ${inboundDelayedPairs.toLocaleString("zh-CN")} 个前序到达延误轮转可用于传播分析。`
  : payload.summary.quality.rotation_warning;
const conclusionText = rotationSufficient
  ? "结论边界：结果仅代表当前覆盖期；延误传播率描述条件相关性，不证明前序延误是唯一原因；缓冲情景为静态测算，未纳入飞机利用率、机组工时和机场时刻约束。"
  : "结论边界：当前数据不足以支持延误传播或缓冲优化结论，仅用于验证清洗、指标口径与可视化流程。";
const scenarioNote = rotationSufficient
  ? "解读：5/10/15分钟缓冲表示在其他条件不变时，后序航班可能从“延误起飞”变为“准点起飞”的数量。该结果用于比较情景，不等同于真实运营收益。"
  : "当前输入缺少足够的连续飞机轮转，因此情景结果仅用于验证计算流程；导入完整BTS月份后会自动刷新。";

function title(sheet, text, context) {
  sheet.showGridLines = false;
  sheet.getRange("A2:H2").merge();
  sheet.getRange("A2").values = [[text]];
  sheet.getRange("A2").format.font = { name: font, size: 16, bold: true, color: navy };
  sheet.getRange("A3:H3").format.borders = { bottom: { style: "thin", color: blue } };
  if (context) {
    sheet.getRange("A4:H4").merge();
    sheet.getRange("A4").values = [[context]];
    sheet.getRange("A4").format.font = { name: font, size: 10, italic: true, color: gray };
  }
}

function sectionHeader(range, text) {
  range.values = [[text]];
  range.format = {
    fill: navy,
    font: { name: font, size: 10, bold: true, color: "#FFFFFF" },
    verticalAlignment: "center",
  };
}

function styleHeader(range) {
  range.format = {
    fill: blue,
    font: { name: font, size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { bottom: { style: "thin", color: "#FFFFFF" } },
  };
}

// Data input sheet -----------------------------------------------------------
inputs.showGridLines = false;
inputs.tabColor = "#98A2B3";
inputs.getRange("A1:B1").values = [["指标", "值"]];
const kpiRows = Object.entries(payload.summary.kpis);
inputs.getRangeByIndexes(1, 0, kpiRows.length, 2).values = kpiRows;
inputs.getRange("D1:J1").values = [[
  "航司", "计划航班", "完成率", "OTP15", "严重延误率", "取消率", "P90到达延误"
]];
const carrierRows = payload.carriers.map(x => [
  x.carrier, x.scheduled_flights, x.completion_rate, x.arrival_otp15,
  x.severe_delay_rate, x.cancellation_rate, x.p90_arrival_delay_minutes,
]);
inputs.getRangeByIndexes(1, 3, carrierRows.length, 7).values = carrierRows;
styleHeader(inputs.getRange("A1:B1"));
styleHeader(inputs.getRange("D1:J1"));
inputs.getRange("E2:I200").format.numberFormat = "0.0%";
inputs.getRange("J2:J200").format.numberFormat = "0.0";
inputs.getRange("A1:J200").format.font = { name: font, size: 9 };
inputs.getRange("A1:J200").format.autofitColumns();
inputs.getRange("A:A").format.columnWidth = 28;
inputs.freezePanes.freezeRows(1);

// Dashboard -----------------------------------------------------------------
dashboard.tabColor = navy;
title(
  dashboard,
  "航班运营分析",
  scopeLabel
);
dashboard.getRange("A6:H6").values = [["计划航班", "", "完成率", "", "到达准点率", "", "取消率", ""]];
dashboard.getRange("A7:H8").format.fill = lightBlue;
dashboard.getRange("A6:B6").merge(); dashboard.getRange("C6:D6").merge();
dashboard.getRange("E6:F6").merge(); dashboard.getRange("G6:H6").merge();
dashboard.getRange("A7:B8").merge(); dashboard.getRange("C7:D8").merge();
dashboard.getRange("E7:F8").merge(); dashboard.getRange("G7:H8").merge();
dashboard.getRange("A7").formulas = [["='数据输入'!B2"]];
dashboard.getRange("C7").formulas = [["='数据输入'!B4"]];
dashboard.getRange("E7").formulas = [["='数据输入'!B5"]];
dashboard.getRange("G7").formulas = [["='数据输入'!B6"]];
dashboard.getRange("A6:H6").format = {
  fill: navy, font: { name: font, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center"
};
dashboard.getRange("A7:H8").format.font = { name: font, size: 16, bold: true, color: navy };
dashboard.getRange("A7:H8").format.horizontalAlignment = "center";
dashboard.getRange("A7:H8").format.verticalAlignment = "center";
dashboard.getRange("A7:B8").format.numberFormat = "#,##0";
dashboard.getRange("C7:H8").format.numberFormat = "0.0%";

dashboard.getRange("A10:H10").merge();
sectionHeader(dashboard.getRange("A10"), "样本适用性");
dashboard.getRange("A11:H12").merge();
dashboard.getRange("A11").values = [[qualityText]];
dashboard.getRange("A11:H12").format = {
  fill: rotationSufficient ? "#E8F5E9" : lightAmber,
  font: { name: font, size: 10, bold: true, color: rotationSufficient ? green : "#7A4E00" },
  wrapText: true, verticalAlignment: "center",
};

dashboard.getRange("A14:G14").values = [["航司", "计划航班", "完成率", "OTP15", "严重延误率", "取消率", "P90延误"]];
const topCarrier = carrierRows.slice(0, 12);
dashboard.getRangeByIndexes(14, 0, topCarrier.length, 7).values = topCarrier;
styleHeader(dashboard.getRange("A14:G14"));
dashboard.getRange("B15:B26").format.numberFormat = "#,##0";
dashboard.getRange("C15:F26").format.numberFormat = "0.0%";
dashboard.getRange("G15:G26").format.numberFormat = "0.0";
dashboard.getRange("A14:G26").format.font = { name: font, size: 10 };
dashboard.getRange("A15:G26").format.borders = { insideHorizontal: { style: "thin", color: "#D0D5DD" } };
dashboard.getRange("A15:G26").conditionalFormats.add("expression", {
  formula: "=$F15>0.03", format: { fill: lightRed, font: { color: red } }
});

const carrierChart = dashboard.charts.add("bar", [
  dashboard.getRange("A14:A26"), dashboard.getRange("D14:D26")
]);
carrierChart.title = "主要航司到达准点率";
carrierChart.titleTextStyle.typeface = font;
carrierChart.hasLegend = false;
carrierChart.xAxis = { axisType: "textAxis", textStyle: { typeface: font, fontSize: 9 } };
carrierChart.yAxis = { numberFormatCode: "0%", numberFormatSourceLinked: false, textStyle: { typeface: font } };
carrierChart.series.items[0].fill = blue;
carrierChart.setPosition("A31", "H46");

dashboard.getRange("A28:H29").merge();
dashboard.getRange("A28").values = [[conclusionText]];
dashboard.getRange("A28:H29").format = { fill: lightGray, font: { name: font, size: 10, color: gray }, wrapText: true };
dashboard.getRange("A:H").format.columnWidth = 10;
dashboard.getRange("A:A").format.columnWidth = 12;
dashboard.getRange("A2:P30").format.verticalAlignment = "center";

// Scenarios -----------------------------------------------------------------
scenarios.tabColor = amber;
title(scenarios, "周转缓冲情景", "静态情景：计划起飞时间后移5/10/15分钟；不代表真实运营效果");
scenarios.getRange("A6:G6").values = [[
  "缓冲分钟", "基线延误起飞", "模拟延误起飞", "可能覆盖航班", "相对降幅", "新增计划分钟", "样本是否充分"
]];
const scenarioRows = payload.scenarios.map(x => [
  x.buffer_minutes, x.baseline_delayed_departures, x.simulated_delayed_departures,
  x.potentially_covered_departures, x.relative_reduction, x.additional_schedule_minutes,
  x.sample_sufficient ? "是" : "否",
]);
scenarios.getRangeByIndexes(6, 0, scenarioRows.length, 7).values = scenarioRows;
styleHeader(scenarios.getRange("A6:G6"));
scenarios.getRange("A7:G10").format.font = { name: font, size: 10 };
scenarios.getRange("A7:D10").format.numberFormat = "#,##0";
scenarios.getRange("E7:E10").format.numberFormat = "0.0%";
scenarios.getRange("F7:F10").format.numberFormat = "#,##0";
scenarios.getRange("G7:G10").conditionalFormats.add("containsText", {
  text: "否", format: { fill: lightRed, font: { color: red, bold: true } }
});
scenarios.getRange("A12:G14").merge();
scenarios.getRange("A12").values = [[scenarioNote]];
scenarios.getRange("A12:G14").format = {
  fill: rotationSufficient ? lightBlue : lightAmber,
  font: { name: font, color: rotationSufficient ? navy : "#7A4E00", bold: true }, wrapText: true
};
const scenarioChart = scenarios.charts.add("line", scenarios.getRange("A6:D10"));
scenarioChart.title = "缓冲时间与延误起飞数";
scenarioChart.titleTextStyle.typeface = font;
scenarioChart.legend = { position: "top", textStyle: { typeface: font } };
scenarioChart.xAxis = { axisType: "textAxis", textStyle: { typeface: font } };
scenarioChart.yAxis = { numberFormatCode: "#,##0", numberFormatSourceLinked: false, textStyle: { typeface: font } };
scenarioChart.setPosition("A16", "G30");
scenarios.getRange("A:G").format.columnWidth = 10;
scenarios.getRange("B:F").format.columnWidth = 12;

// Route risk ----------------------------------------------------------------
routes.tabColor = blue;
title(routes, "高风险航线", "当前覆盖期内的优先级排序；风险评分用于筛查，不是行业标准或因果模型");
routes.getRange("A6:I6").values = [[
  "航线", "计划航班", "到达延误率", "严重延误率", "取消率", "P90延误", "传播率", "吸收率", "风险评分"
]];
const routeRows = payload.routes.slice(0, 40).map(x => [
  x.route, x.scheduled_flights, x.arrival_delay_rate, x.severe_delay_rate,
  x.cancellation_rate, x.p90_arrival_delay, x.propagation_rate,
  x.absorption_rate, x.risk_score,
]);
routes.getRangeByIndexes(6, 0, routeRows.length, 9).values = routeRows;
styleHeader(routes.getRange("A6:I6"));
routes.getRange("A7:I46").format.font = { name: font, size: 9 };
routes.getRange("B7:B46").format.numberFormat = "#,##0";
routes.getRange("C7:E46").format.numberFormat = "0.0%";
routes.getRange("G7:H46").format.numberFormat = "0.0%";
routes.getRange("F7:F46").format.numberFormat = "0.0";
routes.getRange("I7:I46").format.numberFormat = "0.0";
routes.getRange("I7:I46").conditionalFormats.add("colorScale", {
  colors: ["#E8F5E9", "#FFF3CD", "#F8D7DA"], thresholds: ["min", { type: "percentile", value: 50 }, "max"]
});
routes.getRange("A6:I46").format.autofitColumns();
routes.getRange("G:H").format.columnWidth = 10;
routes.freezePanes.freezeRows(6);

// Metrics --------------------------------------------------------------------
metrics.tabColor = green;
title(metrics, "指标字典", "口径先于结论；每个比率都明确分子、分母、粒度和排除规则");
metrics.getRange("A6:D6").values = [["指标", "定义", "粒度", "边界与说明"]];
const metricRows = payload.metrics.map(x => [x["指标"], x["定义"], x["粒度"], x["边界与说明"]]);
metrics.getRangeByIndexes(6, 0, metricRows.length, 4).values = metricRows;
styleHeader(metrics.getRange("A6:D6"));
metrics.getRange("A7:D20").format = { font: { name: font, size: 10 }, wrapText: true, verticalAlignment: "top" };
metrics.getRange("A7:D15").format.borders = { insideHorizontal: { style: "thin", color: "#D0D5DD" } };
metrics.getRange("A:A").format.columnWidth = 14;
metrics.getRange("B:B").format.columnWidth = 30;
metrics.getRange("C:C").format.columnWidth = 8;
metrics.getRange("D:D").format.columnWidth = 24;
metrics.getRange("E:H").format.columnWidth = 2;
metrics.getRange("A7:D15").format.autofitRows();
metrics.freezePanes.freezeRows(6);

// Sources --------------------------------------------------------------------
sources.tabColor = "#98A2B3";
title(sources, "来源与限制", "更新数据后重新运行分析脚本和工作簿构建脚本");
sources.getRange("A6:B6").values = [["项目", "内容"]];
sources.getRange("A7:B14").values = [
  ["官方数据源", payload.source.official],
  ["备用演示镜像", payload.source.sample_mirror],
  ["本次输入文件", payload.summary.scope.sources.join(", ")],
  ["覆盖起始", payload.summary.scope.date_start],
  ["覆盖结束", payload.summary.scope.date_end],
  ["是否完整年度", payload.summary.scope.is_full_year ? "是" : "否"],
  ["传播样本充分", payload.summary.quality.rotation_sample_sufficient ? "是" : "否"],
  ["关键限制", rotationSufficient ? "结果仅代表覆盖期；传播为相关性，缓冲为静态情景。" : payload.summary.quality.rotation_warning],
];
styleHeader(sources.getRange("A6:B6"));
sources.getRange("A7:B14").format = { font: { name: font, size: 10 }, wrapText: true, verticalAlignment: "top" };
sources.getRange("A:A").format.columnWidth = 14;
sources.getRange("B:B").format.columnWidth = 50;
sources.getRange("C:H").format.columnWidth = 2;
sources.getRange("A7:B14").format.autofitRows();
sources.getRange("A17:B17").values = [["检查", "结果"]];
sources.getRange("A18:B20").values = [
  ["航司计划航班合计", null],
  ["总览计划航班", null],
  ["差异", null],
];
sources.getRange("B18").formulas = [[`=SUM('数据输入'!E2:E${carrierRows.length + 1})`]];
sources.getRange("B19").formulas = [["='数据输入'!B2"]];
sources.getRange("B20").formulas = [["=B18-B19"]];
styleHeader(sources.getRange("A17:B17"));
sources.getRange("B20").conditionalFormats.add("cellIs", {
  operator: "notEqual", formula: 0, format: { fill: lightRed, font: { color: red, bold: true } }
});

for (const sheet of [dashboard, scenarios, routes, metrics, sources, inputs]) {
  const used = sheet.getUsedRange();
  if (used) used.format.verticalAlignment = "center";
}

wb.recalculate();

const inspectDashboard = await wb.inspect({
  kind: "table", sheetId: dashboard.name, range: "A2:H29", include: "values,formulas",
  tableMaxRows: 30, tableMaxCols: 8, maxChars: 8000,
});
console.log(inspectDashboard.ndjson);
const errorScan = await wb.inspect({
  kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 }, summary: "final formula error scan",
});
console.log(errorScan.ndjson);

console.log("starting export");
const output = await SpreadsheetFile.exportXlsx(wb);
await output.save(path.join(outputDir, "航空运营分析.xlsx"));
console.log(`saved ${path.join(outputDir, "航空运营分析.xlsx")}`);

if (process.env.RENDER_PREVIEWS === "1") {
  console.log("starting previews");
  for (const sheetName of ["运营总览", "缓冲情景", "高风险航线", "指标字典", "来源与限制"]) {
    console.log(`render ${sheetName}`);
    const preview = await wb.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
    await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
}

