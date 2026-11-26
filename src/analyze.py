"""Build the flight delay propagation portfolio outputs from BTS-style CSVs.

The loader accepts official BTS column names and common snake_case variants.
It keeps conclusions scoped to the supplied files; it never labels a sample as
a full-year result.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import zipfile
from dataclasses import dataclass

import numpy as np
import pandas as pd


COLUMN_ALIASES = {
    "flight_date": ["flightdate", "fl_date", "flight_date"],
    "carrier": ["reporting_airline", "op_unique_carrier", "op_carrier", "carrier"],
    "tail_number": ["tail_number", "tail_num", "tailnum"],
    "flight_number": ["flight_number_reporting_airline", "op_carrier_fl_num", "flightnum"],
    "origin": ["origin"],
    "destination": ["dest", "destination"],
    "scheduled_departure": ["crsdeptime", "crs_dep_time"],
    "actual_departure": ["deptime", "dep_time"],
    "departure_delay": ["depdelay", "dep_delay"],
    "scheduled_arrival": ["crsarrtime", "crs_arr_time"],
    "actual_arrival": ["arrtime", "arr_time"],
    "arrival_delay": ["arrdelay", "arr_delay"],
    "cancelled": ["cancelled"],
    "diverted": ["diverted"],
    "carrier_delay": ["carrierdelay", "carrier_delay"],
    "weather_delay": ["weatherdelay", "weather_delay"],
    "nas_delay": ["nasdelay", "nas_delay"],
    "security_delay": ["securitydelay", "security_delay"],
    "late_aircraft_delay": ["lateaircraftdelay", "late_aircraft_delay"],
    "distance": ["distance"],
}

REQUIRED = {
    "flight_date",
    "carrier",
    "tail_number",
    "origin",
    "destination",
    "scheduled_departure",
    "scheduled_arrival",
    "departure_delay",
    "arrival_delay",
    "cancelled",
}


def canonical_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def find_column(columns: list[str], aliases: list[str]) -> str | None:
    lookup = {canonical_name(column): column for column in columns}
    for alias in aliases:
        if canonical_name(alias) in lookup:
            return lookup[canonical_name(alias)]
    return None


def hhmm_to_minutes(value: object) -> float:
    if pd.isna(value):
        return np.nan
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return np.nan
    if number == 2400:
        return 24 * 60
    hours, minutes = divmod(number, 100)
    if hours not in range(24) or minutes not in range(60):
        return np.nan
    return hours * 60 + minutes


def read_input(path: pathlib.Path) -> pd.DataFrame:
    def selected_columns(columns: list[str]) -> list[str]:
        selected = []
        for aliases in COLUMN_ALIASES.values():
            source = find_column(columns, aliases)
            if source and source not in selected:
                selected.append(source)
        return selected

    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError(f"no CSV found in {path}")
            with archive.open(csv_names[0]) as stream:
                header = list(pd.read_csv(stream, nrows=0, encoding_errors="replace").columns)
            with archive.open(csv_names[0]) as stream:
                return pd.read_csv(
                    stream, usecols=selected_columns(header), low_memory=False,
                    encoding_errors="replace"
                )
    header = list(pd.read_csv(path, nrows=0, encoding_errors="replace").columns)
    return pd.read_csv(
        path, usecols=selected_columns(header), low_memory=False,
        encoding_errors="replace"
    )


def load_flights(paths: list[pathlib.Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        raw = read_input(path)
        rename = {}
        for target, aliases in COLUMN_ALIASES.items():
            source = find_column(list(raw.columns), aliases)
            if source:
                rename[source] = target
        frame = raw.rename(columns=rename)
        missing = REQUIRED - set(frame.columns)
        if missing:
            raise ValueError(f"{path} missing required columns: {sorted(missing)}")
        for optional in set(COLUMN_ALIASES) - set(frame.columns):
            frame[optional] = np.nan
        frames.append(frame[list(COLUMN_ALIASES)])
    flights = pd.concat(frames, ignore_index=True)
    flights["flight_date"] = pd.to_datetime(flights["flight_date"], errors="coerce")
    numeric = [
        "scheduled_departure", "actual_departure", "departure_delay",
        "scheduled_arrival", "actual_arrival", "arrival_delay", "cancelled",
        "diverted", "carrier_delay", "weather_delay", "nas_delay",
        "security_delay", "late_aircraft_delay", "distance",
    ]
    for column in numeric:
        flights[column] = pd.to_numeric(flights[column], errors="coerce")
    flights["cancelled"] = flights["cancelled"].fillna(0).astype(int)
    flights["diverted"] = flights["diverted"].fillna(0).astype(int)
    flights = flights.dropna(subset=["flight_date", "carrier", "origin", "destination"])
    flights["flight_id"] = np.arange(1, len(flights) + 1)
    return flights


def add_timestamps(flights: pd.DataFrame) -> pd.DataFrame:
    result = flights.copy()
    for time_col, output_col in [
        ("scheduled_departure", "scheduled_departure_ts"),
        ("scheduled_arrival", "scheduled_arrival_ts"),
        ("actual_departure", "actual_departure_ts"),
        ("actual_arrival", "actual_arrival_ts"),
    ]:
        minutes = result[time_col].map(hhmm_to_minutes)
        result[output_col] = result["flight_date"] + pd.to_timedelta(minutes, unit="m")
    scheduled_overnight = (
        result["scheduled_arrival_ts"].notna()
        & result["scheduled_departure_ts"].notna()
        & (result["scheduled_arrival_ts"] < result["scheduled_departure_ts"])
    )
    result.loc[scheduled_overnight, "scheduled_arrival_ts"] += pd.Timedelta(days=1)
    actual_overnight = (
        result["actual_arrival_ts"].notna()
        & result["actual_departure_ts"].notna()
        & (result["actual_arrival_ts"] < result["actual_departure_ts"])
    )
    result.loc[actual_overnight, "actual_arrival_ts"] += pd.Timedelta(days=1)
    result["operated"] = ((result["cancelled"] == 0) & (result["diverted"] == 0)).astype(int)
    result["arrival_delayed_15"] = (
        (result["operated"] == 1) & (result["arrival_delay"] >= 15)
    ).astype(int)
    result["departure_delayed_15"] = (
        (result["operated"] == 1) & (result["departure_delay"] >= 15)
    ).astype(int)
    result["severe_delay_60"] = (
        (result["operated"] == 1) & (result["arrival_delay"] >= 60)
    ).astype(int)
    result["route"] = result["origin"].astype(str) + "-" + result["destination"].astype(str)
    return result


def build_rotation_pairs(flights: pd.DataFrame) -> pd.DataFrame:
    sequenced = flights.dropna(subset=["tail_number", "scheduled_departure_ts"]).copy()
    sequenced = sequenced.sort_values(["tail_number", "scheduled_departure_ts", "flight_id"])
    group = sequenced.groupby("tail_number", sort=False)
    previous = {
        "prev_flight_id": group["flight_id"].shift(),
        "prev_destination": group["destination"].shift(),
        "prev_scheduled_arrival_ts": group["scheduled_arrival_ts"].shift(),
        "prev_actual_arrival_ts": group["actual_arrival_ts"].shift(),
        "prev_arrival_delay": group["arrival_delay"].shift(),
        "prev_operated": group["operated"].shift(),
        "prev_route": group["route"].shift(),
    }
    for column, values in previous.items():
        sequenced[column] = values
    sequenced["scheduled_ground_minutes"] = (
        sequenced["scheduled_departure_ts"] - sequenced["prev_scheduled_arrival_ts"]
    ).dt.total_seconds() / 60
    sequenced["actual_ground_minutes"] = (
        sequenced["actual_departure_ts"] - sequenced["prev_actual_arrival_ts"]
    ).dt.total_seconds() / 60
    sequenced["valid_rotation"] = (
        (sequenced["origin"] == sequenced["prev_destination"])
        & (sequenced["prev_operated"] == 1)
        & (sequenced["operated"] == 1)
        & sequenced["scheduled_ground_minutes"].between(0, 720, inclusive="both")
    )
    sequenced["eligible_inbound_delay"] = (
        sequenced["valid_rotation"] & (sequenced["prev_arrival_delay"] >= 15)
    )
    sequenced["propagated"] = (
        sequenced["eligible_inbound_delay"] & (sequenced["departure_delay"] >= 15)
    )
    sequenced["absorbed"] = (
        sequenced["eligible_inbound_delay"] & (sequenced["departure_delay"] < 15)
    )
    sequenced["recovered_minutes"] = np.where(
        sequenced["valid_rotation"],
        np.maximum(sequenced["prev_arrival_delay"].fillna(0) - sequenced["departure_delay"].fillna(0), 0),
        np.nan,
    )
    return sequenced


def safe_rate(numerator: float, denominator: float) -> float | None:
    if denominator == 0 or pd.isna(denominator):
        return None
    return float(numerator / denominator)


def summarize(flights: pd.DataFrame, pairs: pd.DataFrame, source_names: list[str]) -> dict:
    operated = flights[flights["operated"] == 1]
    valid_pairs = pairs[pairs["valid_rotation"]]
    inbound = pairs[pairs["eligible_inbound_delay"]]
    result = {
        "scope": {
            "sources": source_names,
            "date_start": flights["flight_date"].min().date().isoformat(),
            "date_end": flights["flight_date"].max().date().isoformat(),
            "is_full_year": bool(
                flights["flight_date"].min().month == 1
                and flights["flight_date"].max().month == 12
                and flights["flight_date"].min().year == flights["flight_date"].max().year
            ),
        },
        "kpis": {
            "scheduled_flights": int(len(flights)),
            "operated_flights": int(len(operated)),
            "completion_rate": safe_rate(len(operated), len(flights)),
            "arrival_otp15": safe_rate((operated["arrival_delay"] < 15).sum(), operated["arrival_delay"].notna().sum()),
            "cancellation_rate": safe_rate((flights["cancelled"] == 1).sum(), len(flights)),
            "severe_delay_rate": safe_rate((operated["arrival_delay"] >= 60).sum(), operated["arrival_delay"].notna().sum()),
            "p90_arrival_delay_minutes": float(operated["arrival_delay"].dropna().quantile(0.90)),
            "valid_rotation_pairs": int(len(valid_pairs)),
            "inbound_delayed_pairs": int(len(inbound)),
            "propagation_rate": safe_rate(inbound["propagated"].sum(), len(inbound)),
            "absorption_rate": safe_rate(inbound["absorbed"].sum(), len(inbound)),
            "median_recovered_minutes": float(valid_pairs["recovered_minutes"].dropna().median()),
        },
        "quality": {
            "rotation_sample_sufficient": bool(len(valid_pairs) >= 30 and len(inbound) >= 30),
            "rotation_warning": (
                None if len(valid_pairs) >= 30 and len(inbound) >= 30
                else "输入是跨年份抽样数据，连续机尾号轮转不足；运营KPI可用于演示，传播率与缓冲情景不可作为业务结论。"
            ),
        },
    }
    return result


def carrier_summary(flights: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for carrier, group in flights.groupby("carrier"):
        operated = group[group["operated"] == 1]
        rows.append({
            "carrier": carrier,
            "scheduled_flights": len(group),
            "completion_rate": safe_rate(len(operated), len(group)),
            "arrival_otp15": safe_rate((operated["arrival_delay"] < 15).sum(), operated["arrival_delay"].notna().sum()),
            "severe_delay_rate": safe_rate((operated["arrival_delay"] >= 60).sum(), operated["arrival_delay"].notna().sum()),
            "cancellation_rate": safe_rate((group["cancelled"] == 1).sum(), len(group)),
            "p90_arrival_delay_minutes": operated["arrival_delay"].dropna().quantile(0.90),
        })
    return pd.DataFrame(rows).sort_values("scheduled_flights", ascending=False)


def route_risk_summary(flights: pd.DataFrame, pairs: pd.DataFrame, minimum_flights: int = 20) -> pd.DataFrame:
    pair_agg = pairs[pairs["valid_rotation"]].groupby("route").agg(
        valid_rotation_pairs=("flight_id", "size"),
        inbound_delayed_pairs=("eligible_inbound_delay", "sum"),
        propagated_pairs=("propagated", "sum"),
        absorption_pairs=("absorbed", "sum"),
    ).reset_index()
    base = flights.groupby(["route", "origin", "destination"]).agg(
        scheduled_flights=("flight_id", "size"),
        operated_flights=("operated", "sum"),
        arrival_delayed_15=("arrival_delayed_15", "sum"),
        severe_delays=("severe_delay_60", "sum"),
        cancellations=("cancelled", "sum"),
        p90_arrival_delay=("arrival_delay", lambda s: s.dropna().quantile(0.90)),
    ).reset_index()
    result = base.merge(pair_agg, on="route", how="left").fillna(0)
    result = result[result["scheduled_flights"] >= minimum_flights].copy()
    result["arrival_delay_rate"] = result["arrival_delayed_15"] / result["operated_flights"].replace(0, np.nan)
    result["severe_delay_rate"] = result["severe_delays"] / result["operated_flights"].replace(0, np.nan)
    result["cancellation_rate"] = result["cancellations"] / result["scheduled_flights"]
    result["propagation_rate"] = result["propagated_pairs"] / result["inbound_delayed_pairs"].replace(0, np.nan)
    result["absorption_rate"] = result["absorption_pairs"] / result["inbound_delayed_pairs"].replace(0, np.nan)
    risk_columns = ["arrival_delay_rate", "severe_delay_rate", "cancellation_rate", "p90_arrival_delay"]
    for column in risk_columns:
        minimum = result[column].min()
        maximum = result[column].max()
        result[f"{column}_scaled"] = 0 if maximum == minimum else (result[column] - minimum) / (maximum - minimum)
    result["risk_score"] = 100 * (
        0.30 * result["arrival_delay_rate_scaled"]
        + 0.25 * result["severe_delay_rate_scaled"]
        + 0.20 * result["cancellation_rate_scaled"]
        + 0.15 * result["p90_arrival_delay_scaled"]
        + 0.10 * result["propagation_rate"].fillna(0)
    )
    keep = [
        "route", "origin", "destination", "scheduled_flights", "arrival_delay_rate",
        "severe_delay_rate", "cancellation_rate", "p90_arrival_delay",
        "valid_rotation_pairs", "inbound_delayed_pairs", "propagation_rate",
        "absorption_rate", "risk_score",
    ]
    return result[keep].sort_values(["risk_score", "scheduled_flights"], ascending=[False, False])


def scenario_summary(pairs: pd.DataFrame) -> pd.DataFrame:
    eligible = pairs[pairs["valid_rotation"] & pairs["departure_delay"].notna()].copy()
    baseline = int((eligible["departure_delay"] >= 15).sum())
    rows = []
    for buffer_minutes in (0, 5, 10, 15):
        adjusted_delay = eligible["departure_delay"] - buffer_minutes
        delayed = int((adjusted_delay >= 15).sum())
        rows.append({
            "buffer_minutes": buffer_minutes,
            "baseline_delayed_departures": baseline,
            "simulated_delayed_departures": delayed,
            "potentially_covered_departures": baseline - delayed,
            "relative_reduction": safe_rate(baseline - delayed, baseline),
            "additional_schedule_minutes": int(buffer_minutes * len(eligible)),
            "covered_per_1000_added_minutes": safe_rate((baseline - delayed) * 1000, buffer_minutes * len(eligible)),
            "sample_sufficient": bool(len(eligible) >= 30 and baseline >= 30),
        })
    return pd.DataFrame(rows)


def metric_dictionary() -> pd.DataFrame:
    return pd.DataFrame([
        ["到达准点率 OTP15", "到达延误<15分钟的正常完成航班 / 有到达延误记录的正常完成航班", "航班", "取消及备降航班不进入分母"],
        ["航班完成率", "未取消且未备降航班 / 计划航班", "航班", "用于衡量计划执行"],
        ["取消率", "取消航班 / 计划航班", "航班", "取消航班不以0分钟延误计入准点率"],
        ["严重延误率", "到达延误>=60分钟航班 / 有到达延误记录的正常完成航班", "航班", "阈值为项目口径"],
        ["有效轮转对", "同一机尾号的相邻航班，且前序目的地=后序始发地，计划间隔0-720分钟", "航段对", "近似还原飞机轮转，不等同于航司正式排班"],
        ["延误传播率", "前序到达延误>=15分钟且后序起飞延误>=15分钟的轮转对 / 前序到达延误>=15分钟的轮转对", "航段对", "描述相关传播，不证明因果"],
        ["延误吸收率", "前序到达延误>=15分钟且后序起飞延误<15分钟的轮转对 / 前序到达延误>=15分钟的轮转对", "航段对", "与传播率互补"],
        ["风险评分", "延误率30%+严重延误率25%+取消率20%+P90延误15%+传播率10%", "航线", "各分项先做样本内Min-Max标准化；仅用于排序"],
        ["缓冲覆盖航班", "基线起飞延误>=15分钟、增加假设缓冲后低于15分钟的有效轮转航班", "航班", "静态情景模拟，不代表真实运营效果"],
    ], columns=["指标", "定义", "粒度", "边界与说明"])


def write_outputs(output_dir: pathlib.Path, flights: pd.DataFrame, pairs: pd.DataFrame, summary: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    carrier = carrier_summary(flights)
    routes = route_risk_summary(flights, pairs)
    scenarios = scenario_summary(pairs)
    metrics = metric_dictionary()
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    carrier.to_csv(output_dir / "carrier_kpis.csv", index=False, encoding="utf-8-sig")
    routes.to_csv(output_dir / "route_risk.csv", index=False, encoding="utf-8-sig")
    scenarios.to_csv(output_dir / "buffer_scenarios.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(output_dir / "metric_dictionary.csv", index=False, encoding="utf-8-sig")
    payload = {
        "summary": summary,
        "carriers": carrier.astype(object).where(pd.notna(carrier), None).to_dict(orient="records"),
        "routes": routes.head(100).astype(object).where(pd.notna(routes.head(100)), None).to_dict(orient="records"),
        "scenarios": scenarios.astype(object).where(pd.notna(scenarios), None).to_dict(orient="records"),
        "metrics": metrics.to_dict(orient="records"),
        "source": {
            "official": "https://www.transtats.bts.gov/ONTIME/",
            "sample_mirror": "https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/IBMDeveloperSkillsNetwork-DV0101EN-SkillsNetwork/Data%20Files/airline_data.csv",
        },
    }
    (output_dir / "workbook_payload.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pair_columns = [
        "flight_id", "prev_flight_id", "flight_date", "tail_number", "carrier", "route",
        "prev_route", "scheduled_ground_minutes", "prev_arrival_delay", "departure_delay",
        "valid_rotation", "eligible_inbound_delay", "propagated", "absorbed", "recovered_minutes",
    ]
    pairs[pair_columns].head(5000).to_csv(output_dir / "rotation_pairs_sample.csv", index=False, encoding="utf-8-sig")
    powerbi = output_dir / "powerbi"
    powerbi.mkdir(exist_ok=True)
    carrier.to_csv(powerbi / "carrier_kpis.csv", index=False, encoding="utf-8-sig")
    routes.head(500).to_csv(powerbi / "route_risk.csv", index=False, encoding="utf-8-sig")
    scenarios.to_csv(powerbi / "buffer_scenarios.csv", index=False, encoding="utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", type=pathlib.Path, nargs="+")
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path("data/processed"))
    args = parser.parse_args()
    flights = add_timestamps(load_flights(args.inputs))
    pairs = build_rotation_pairs(flights)
    summary = summarize(flights, pairs, [path.name for path in args.inputs])
    write_outputs(args.output_dir, flights, pairs, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

