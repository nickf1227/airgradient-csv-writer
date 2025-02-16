#!/usr/bin/env python3
import argparse
import csv
import datetime
import sys
import statistics
from datetime import timedelta

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
                    # Parse timestamp (expects ISO format, e.g. "2025-02-08T23:13:23.004531")
                    ts = datetime.datetime.fromisoformat(row["timestamp"])
                    # Convert atmpCompensated from Celsius to Fahrenheit.
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

    # Define the metrics we care about.
    metrics = ["atmpCompensated_F", "rhumCompensated", "tvocIndex", "rco2", "pm02Compensated"]
    metric_names = {
        "atmpCompensated_F": "Temperature (°F)",
        "rhumCompensated": "Relative Humidity (%)",
        "tvocIndex": "TVOC Index",
        "rco2": "eCO2 (ppm)",
        "pm02Compensated": "PM2.5 (µg/m³)"
    }

    results = {}
    for metric in metrics:
        current_value = current_entry[metric]
        avg_1d = compute_rolling_average(data, metric, 1, current_time)
        avg_7d = compute_rolling_average(data, metric, 7, current_time)
        # Compute stats for the last 7 days.
        (min_val, min_ts, max_val, max_ts, median_val, count_7d, std_dev, range_val) = compute_window_stats(data, metric, 7, current_time)
        # Compute outliers (using all available data)
        outliers = detect_outliers(data, metric)

        # Compute trend statistics if 7-day average is available and nonzero.
        if avg_7d and avg_7d != 0:
            trend_percent = ((avg_1d - avg_7d) / avg_7d) * 100
            deviation_percent = ((current_value - avg_7d) / avg_7d) * 100
        else:
            trend_percent = None
            deviation_percent = None

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
            "outliers": outliers
        }

    # Build the ASCII report with creative separators and reorganization.
    report_lines = []
    report_lines.append("=" * 50)
    report_lines.append("      Air Gradient Sensor Report")
    report_lines.append("=" * 50)
    report_lines.append("File: {}".format(args.file))
    report_lines.append("Report Generated on: {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    report_lines.append("=" * 50)
    report_lines.append("")

    for metric in metrics:
        name = metric_names.get(metric, metric)
        stats = results[metric]
        report_lines.append("-" * 50)
        report_lines.append("[ Metric: {} ]".format(name))
        report_lines.append("-" * 50)
        report_lines.append(">> Current Reading:")
        report_lines.append("   Value: {:.2f} at {}".format(
            stats["current_value"], format_timestamp(stats["current_timestamp"])))
        report_lines.append("")
        report_lines.append(">> Rolling Averages:")
        if stats["rolling_1d"] is not None:
            report_lines.append("   1-day: {:.2f}".format(stats["rolling_1d"]))
        else:
            report_lines.append("   1-day: N/A")
        if stats["rolling_7d"] is not None:
            report_lines.append("   7-day: {:.2f}".format(stats["rolling_7d"]))
        else:
            report_lines.append("   7-day: N/A")
        report_lines.append("")
        report_lines.append(">> Window Statistics (Last 7 Days):")
        if stats["max_value_window"] is not None:
            report_lines.append("   Highest: {:.2f} at {}".format(
                stats["max_value_window"], format_timestamp(stats["max_timestamp_window"])))
        else:
            report_lines.append("   Highest: N/A")
        if stats["min_value_window"] is not None:
            report_lines.append("   Lowest: {:.2f} at {}".format(
                stats["min_value_window"], format_timestamp(stats["min_timestamp_window"])))
        else:
            report_lines.append("   Lowest: N/A")
        if stats["median_7d"] is not None:
            report_lines.append("   Median: {:.2f}".format(stats["median_7d"]))
        else:
            report_lines.append("   Median: N/A")
        report_lines.append("   Count: {}".format(stats["count_7d"]))
        if stats["std_dev_7d"] is not None:
            report_lines.append("   Std Dev: {:.2f}".format(stats["std_dev_7d"]))
        else:
            report_lines.append("   Std Dev: N/A")
        if stats["range_7d"] is not None:
            report_lines.append("   Range: {:.2f}".format(stats["range_7d"]))
        else:
            report_lines.append("   Range: N/A")
        report_lines.append("")
        report_lines.append(">> Trend Analysis:")
        if stats["trend_percent"] is not None:
            report_lines.append("   Trend (1-day vs 7-day): {:+.2f}%".format(stats["trend_percent"]))
        else:
            report_lines.append("   Trend (1-day vs 7-day): N/A")
        if stats["deviation_percent"] is not None:
            report_lines.append("   Deviation from 7-day avg: {:+.2f}%".format(stats["deviation_percent"]))
        else:
            report_lines.append("   Deviation from 7-day avg: N/A")
        report_lines.append("")
        report_lines.append(">> Outlier Analysis:")
        report_lines.append("   Top 5 Worst Outliers:")
        if not stats["outliers"]:
            report_lines.append("     None")
        else:
            for idx, (value, ts) in enumerate(stats["outliers"], start=1):
                report_lines.append("     {}. {:.2f} at {}".format(idx, value, format_timestamp(ts)))
        report_lines.append("")
        report_lines.append("=" * 50)
        report_lines.append("")

    # Print the report to the shell.
    for line in report_lines:
        print(line)

if __name__ == "__main__":
    main()
