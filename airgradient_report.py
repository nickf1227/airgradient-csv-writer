#!/usr/bin/env python3
import argparse
import csv
import datetime
import sys
import statistics
from datetime import timedelta, time

def format_timestamp(ts):
    """Format a datetime object to a human-readable string."""
    return ts.strftime("%Y-%m-%d %H:%M:%S")

def parse_csv(file_path):
    """
    Read the CSV file and extract only the fields we care about:
      - timestamp
      - atmpCompensated (converted to Fahrenheit)
      - rhumCompensated
      - tvocIndex
      - rco2
      - pm02Compensated
    Returns a list of dictionaries.
    """
    data = []
    try:
        with open(file_path, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    # Parse timestamp (expects ISO format)
                    ts = datetime.datetime.fromisoformat(row["timestamp"])
                    # Convert temperature from Celsius to Fahrenheit.
                    temp_c = float(row["atmpCompensated"])
                    temp_f = temp_c * 9 / 5 + 32
                    # Convert other fields to floats.
                    rhum = float(row["rhumCompensated"])
                    tvoc = float(row["tvocIndex"])
                    eco2 = float(row["rco2"])
                    pm02 = float(row["pm02Compensated"])
                    data.append({
                        "timestamp": ts,
                        "atmpCompensated_F": temp_f,
                        "rhumCompensated": rhum,
                        "tvocIndex": tvoc,
                        "rco2": eco2,
                        "pm02Compensated": pm02
                    })
                except Exception:
                    # Skip rows that cannot be parsed.
                    continue
    except Exception as e:
        sys.exit("Error reading CSV file: {}".format(e))
    return data

def compute_rolling_average(data, metric, window_days, current_time):
    """
    Compute the average of values for a given metric over the time window 
    [current_time - window_days, current_time].
    """
    window_start = current_time - timedelta(days=window_days)
    values = [entry[metric] for entry in data if window_start <= entry["timestamp"] <= current_time]
    if values:
        return sum(values) / len(values)
    else:
        return None

def compute_window_stats(data, metric, window_days, current_time):
    """
    Compute statistics over the given window (last window_days) for a metric.
    Returns:
      min_val, min_timestamp, max_val, max_timestamp, median, count, std_dev, range_val
    """
    window_start = current_time - timedelta(days=window_days)
    subset = [entry for entry in data if window_start <= entry["timestamp"] <= current_time]
    if not subset:
        return None, None, None, None, None, 0, None, None
    values = [entry[metric] for entry in subset]
    min_val = min(values)
    max_val = max(values)
    # Get the corresponding timestamps for min and max.
    min_entry = min(subset, key=lambda x: x[metric])
    max_entry = max(subset, key=lambda x: x[metric])
    median_val = statistics.median(values)
    count = len(values)
    std_dev = statistics.stdev(values) if count > 1 else 0
    range_val = max_val - min_val
    return min_val, min_entry["timestamp"], max_val, max_entry["timestamp"], median_val, count, std_dev, range_val

def compute_quartiles(values):
    """
    Compute Q1, median (Q2), and Q3 for a list of numeric values.
    """
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n == 0:
        return None, None, None
    median = statistics.median(sorted_vals)
    if n % 2 == 0:
        lower_half = sorted_vals[: n // 2]
        upper_half = sorted_vals[n // 2 :]
    else:
        lower_half = sorted_vals[: n // 2]
        upper_half = sorted_vals[n // 2 + 1 :]
    Q1 = statistics.median(lower_half) if lower_half else sorted_vals[0]
    Q3 = statistics.median(upper_half) if upper_half else sorted_vals[-1]
    return Q1, median, Q3

def detect_outliers(data, metric):
    """
    Detect potential outliers in the data for a given metric using the IQR method.
    Outliers are sorted by their absolute deviation from the median (i.e. the worst outliers),
    and the function returns only the top 5.
    Returns a list of tuples (value, timestamp).
    """
    values = [entry[metric] for entry in data]
    if not values:
        return []
    Q1, med, Q3 = compute_quartiles(values)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    outliers = []
    for entry in data:
        val = entry[metric]
        if val < lower_bound or val > upper_bound:
            outliers.append((val, entry["timestamp"]))
    # Sort outliers by absolute deviation from the median (largest deviation first)
    outliers.sort(key=lambda x: abs(x[0] - med), reverse=True)
    return outliers[:5]

def compute_segment_stats(data, metric, window_days, current_time, seg_start, seg_end):
    """
    Compute statistics for a given metric for entries whose time-of-day falls between
    seg_start and seg_end over the last window_days.
    Returns a dict with average, median, count, std_dev, min, max, and range.
    """
    window_start = current_time - timedelta(days=window_days)
    # Filter entries that fall within the window and time segment.
    subset = [entry for entry in data 
              if window_start <= entry["timestamp"] <= current_time 
              and seg_start <= entry["timestamp"].time() < seg_end]
    if not subset:
        return None
    values = [entry[metric] for entry in subset]
    avg = sum(values) / len(values)
    median_val = statistics.median(values)
    count = len(values)
    std_dev = statistics.stdev(values) if count > 1 else 0
    min_val = min(values)
    max_val = max(values)
    return {
        "avg": avg,
        "median": median_val,
        "count": count,
        "std_dev": std_dev,
        "min": min_val,
        "max": max_val,
        "range": max_val - min_val
    }

def main():
    parser = argparse.ArgumentParser(description="Generate an ASCII report from an Air Gradient CSV file.")
    parser.add_argument("--file", default="/mnt/fire/tn_scripts/airgradient.csv",
                        help="Path to the CSV file (default: /mnt/fire/tn_scripts/airgradient.csv)")
    args = parser.parse_args()

    data = parse_csv(args.file)
    if not data:
        sys.exit("No data found in CSV file.")

    # Sort data by timestamp.
    data.sort(key=lambda x: x["timestamp"])
    current_entry = data[-1]
    current_time = current_entry["timestamp"]

    # Define the metrics and friendly names.
    metrics = ["atmpCompensated_F", "rhumCompensated", "tvocIndex", "rco2", "pm02Compensated"]
    metric_names = {
        "atmpCompensated_F": "Temperature (°F)",
        "rhumCompensated": "Relative Humidity (%)",
        "tvocIndex": "TVOC Index",
        "rco2": "eCO2 (ppm)",
        "pm02Compensated": "PM2.5 (µg/m³)"
    }

    # Define time-of-day segments.
    # Night: 00:00-06:00, Morning: 06:00-12:00, Afternoon: 12:00-18:00, Evening: 18:00-24:00.
    segments = {
        "Night": (time(0, 0), time(6, 0)),
        "Morning": (time(6, 0), time(12, 0)),
        "Afternoon": (time(12, 0), time(18, 0)),
        "Evening": (time(18, 0), time(23, 59, 59))
    }

    results = {}
    # Compute overall stats and outliers per metric.
    for metric in metrics:
        current_value = current_entry[metric]
        avg_1d = compute_rolling_average(data, metric, 1, current_time)
        avg_7d = compute_rolling_average(data, metric, 7, current_time)
        # Overall window stats for the last 7 days.
        (min_val, min_ts, max_val, max_ts, median_val, count_7d, std_dev, range_val) = compute_window_stats(data, metric, 7, current_time)
        # Outliers using all available data.
        outliers = detect_outliers(data, metric)

        # Compute trend stats.
        if avg_7d and avg_7d != 0:
            trend_percent = ((avg_1d - avg_7d) / avg_7d) * 100
            deviation_percent = ((current_value - avg_7d) / avg_7d) * 100
        else:
            trend_percent = None
            deviation_percent = None

        # Compute time-of-day segment stats for the last 7 days.
        segment_stats = {}
        for seg_name, (seg_start, seg_end) in segments.items():
            seg_stat = compute_segment_stats(data, metric, 7, current_time, seg_start, seg_end)
            segment_stats[seg_name] = seg_stat

        results[metric] = {
            "current_value": current_value,
            "current_timestamp": current_time,
            "rolling_1d": avg_1d,
            "rolling_7d": avg_7d,
            "min_value_window": min_val,
            "min_timestamp_window": min_ts,
            "max_value_window": max_val,
            "max_timestamp_window": max_ts,
            "median_7d": median_val,
            "count_7d": count_7d,
            "std_dev_7d": std_dev,
            "range_7d": range_val,
            "trend_percent": trend_percent,
            "deviation_percent": deviation_percent,
            "outliers": outliers,
            "segment_stats": segment_stats
        }

    # Build the ASCII report with creative separators.
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append("              Air Gradient Sensor Report")
    report_lines.append("=" * 60)
    report_lines.append("File: {}".format(args.file))
    report_lines.append("Report Generated on: {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    report_lines.append("=" * 60)
    report_lines.append("")

    for metric in metrics:
        name = metric_names.get(metric, metric)
        stats = results[metric]
        report_lines.append("-" * 60)
        report_lines.append("[ Metric: {} ]".format(name))
        report_lines.append("-" * 60)
        report_lines.append(">> Current Reading:")
        report_lines.append("   Value: {:.2f} at {}".format(
            stats["current_value"], format_timestamp(stats["current_timestamp"])))
        report_lines.append("")
        report_lines.append(">> Rolling Averages:")
        report_lines.append("   1-day: {:.2f}".format(stats["rolling_1d"]) if stats["rolling_1d"] is not None else "   1-day: N/A")
        report_lines.append("   7-day: {:.2f}".format(stats["rolling_7d"]) if stats["rolling_7d"] is not None else "   7-day: N/A")
        report_lines.append("")
        report_lines.append(">> Window Statistics (Last 7 Days):")
        report_lines.append("   Highest: {:.2f} at {}".format(
            stats["max_value_window"], format_timestamp(stats["max_timestamp_window"])) if stats["max_value_window"] is not None else "   Highest: N/A")
        report_lines.append("   Lowest: {:.2f} at {}".format(
            stats["min_value_window"], format_timestamp(stats["min_timestamp_window"])) if stats["min_value_window"] is not None else "   Lowest: N/A")
        report_lines.append("   Median: {:.2f}".format(stats["median_7d"]) if stats["median_7d"] is not None else "   Median: N/A")
        report_lines.append("   Count: {}".format(stats["count_7d"]))
        report_lines.append("   Std Dev: {:.2f}".format(stats["std_dev_7d"]) if stats["std_dev_7d"] is not None else "   Std Dev: N/A")
        report_lines.append("   Range: {:.2f}".format(stats["range_7d"]) if stats["range_7d"] is not None else "   Range: N/A")
        report_lines.append("")
        report_lines.append(">> Trend Analysis:")
        report_lines.append("   Trend (1-day vs 7-day): {:+.2f}%".format(stats["trend_percent"]) if stats["trend_percent"] is not None else "   Trend: N/A")
        report_lines.append("   Deviation from 7-day avg: {:+.2f}%".format(stats["deviation_percent"]) if stats["deviation_percent"] is not None else "   Deviation: N/A")
        report_lines.append("")
        report_lines.append(">> Outlier Analysis:")
        report_lines.append("   Top 5 Worst Outliers:")
        if not stats["outliers"]:
            report_lines.append("     None")
        else:
            for idx, (value, ts) in enumerate(stats["outliers"], start=1):
                report_lines.append("     {}. {:.2f} at {}".format(idx, value, format_timestamp(ts)))
        report_lines.append("")
        report_lines.append(">> Time-of-Day Analysis (Last 7 Days):")
        for seg_name in segments:
            seg_stat = stats["segment_stats"].get(seg_name)
            report_lines.append("   [{}]".format(seg_name))
            if seg_stat:
                report_lines.append("      Count: {}".format(seg_stat["count"]))
                report_lines.append("      Avg: {:.2f}".format(seg_stat["avg"]))
                report_lines.append("      Median: {:.2f}".format(seg_stat["median"]))
                report_lines.append("      Min: {:.2f}".format(seg_stat["min"]))
                report_lines.append("      Max: {:.2f}".format(seg_stat["max"]))
                report_lines.append("      Std Dev: {:.2f}".format(seg_stat["std_dev"]))
                report_lines.append("      Range: {:.2f}".format(seg_stat["range"]))
            else:
                report_lines.append("      No data available.")
            report_lines.append("")
        report_lines.append("=" * 60)
        report_lines.append("")

    # Print the report to the shell.
    for line in report_lines:
        print(line)

if __name__ == "__main__":
    main()
