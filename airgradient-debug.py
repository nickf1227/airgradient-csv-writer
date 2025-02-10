import requests
import csv
import time
from datetime import datetime
import os

# ========================
# User Configuration
# ========================
URL = "http://10.69.10.92/measures/current"  # Sensor API URL
OUTPUT_CSV = "./airgradient.csv"             # Output CSV file path
INTERVAL = 60                                # Interval in seconds between queries
NAME = "Basement"                            # Custom name to include in CSV
SAMPLES_PER_INTERVAL = 12                    # Number of samples to take per interval
SAMPLE_INTERVAL = 3                          # Interval in seconds between each sample

def initialize_csv(url, output_file):
    """
    Initialize the CSV file.
    If the file already exists, read and return its headers.
    Otherwise, perform an initial API request to determine the sensor data schema,
    sort the keys alphabetically, and force 'name' and 'serialno' (if present) in the desired order.
    """
    if os.path.isfile(output_file):
        try:
            with open(output_file, 'r', newline='') as f:
                reader = csv.reader(f)
                headers = next(reader, [])
            if not headers:
                raise ValueError("CSV file exists but has no headers.")
            print(f"CSV file '{output_file}' exists; using headers: {headers}")
            return headers
        except Exception as e:
            print(f"Error reading existing CSV: {e}")
            exit(1)
    else:
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            # Get sensor data keys sorted alphabetically.
            data_keys = sorted(data.keys())

            # If 'serialno' is present, remove it and later reinsert it after 'name'.
            if 'serialno' in data_keys:
                data_keys.remove('serialno')
                headers = ['timestamp', 'name', 'serialno'] + data_keys
            else:
                headers = ['timestamp', 'name'] + data_keys

            # Create the CSV file and write the header along with the first data row.
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()

                row = {'timestamp': datetime.now().isoformat(), 'name': NAME}
                for key in headers:
                    if key in ['timestamp', 'name']:
                        continue
                    row[key] = data.get(key, '')
                writer.writerow(row)

            print(f"Created new CSV file at '{output_file}' with headers: {headers}")
            return headers
        except Exception as e:
            print(f"Failed to initialize CSV: {e}")
            exit(1)

def get_samples(url, num_samples, sample_interval):
    """
    Get multiple samples from the sensor API, each with a timestamp.
    Returns a list of tuples (timestamp, data_dict).
    """
    samples = []
    for _ in range(num_samples):
        try:
            sample_time = datetime.now().isoformat()
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            samples.append((sample_time, data))
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        time.sleep(sample_interval)
    return samples

def average_samples(samples):
    """
    For each key in the samples:
      - If numeric values exist and there are at least 3 values, discard the highest and lowest,
        average the remainder, and round the result to 2 decimal places.
      - If there are numeric values but fewer than 3, average them and round the result.
      - Otherwise, for non-numeric fields, use the first encountered non-numeric value.
    """
    if len(samples) < 3:
        raise ValueError("Not enough samples to average")
    
    averaged_data = {}
    # Get all unique keys from the samples
    keys = set()
    for sample in samples:
        keys.update(sample.keys())
    
    for key in keys:
        numeric_values = []
        non_numeric_value = None
        
        for sample in samples:
            if key in sample:
                value = sample[key]
                try:
                    # Attempt to convert to float
                    num = float(value)
                    numeric_values.append(num)
                except (ValueError, TypeError):
                    # Save the first non-numeric value encountered
                    if non_numeric_value is None:
                        non_numeric_value = value
        
        if len(numeric_values) >= 3:
            numeric_values.sort()
            trimmed = numeric_values[1:-1]  # Discard the highest and lowest
            avg = sum(trimmed) / len(trimmed)
            averaged_data[key] = round(avg, 2)
        elif numeric_values:
            # Average if there are numeric values but fewer than 3 samples
            avg = sum(numeric_values) / len(numeric_values)
            averaged_data[key] = round(avg, 2)
        elif non_numeric_value is not None:
            # For non-numeric fields, just use the first encountered value
            averaged_data[key] = non_numeric_value
    
    return averaged_data

def main():
    headers = initialize_csv(URL, OUTPUT_CSV)

    # Main collection loop
    while True:
        try:
            start_time = time.time()
            raw_samples = get_samples(URL, SAMPLES_PER_INTERVAL, SAMPLE_INTERVAL)
            if len(raw_samples) < SAMPLES_PER_INTERVAL:
                print("Not enough samples collected; skipping entry.")
                continue  # Skip to next iteration without sleeping full INTERVAL

            samples_data = [data for (ts, data) in raw_samples]
            averaged_data = average_samples(samples_data)
            current_time = datetime.now().isoformat()

            # Prepare the row with the configured timestamp and name.
            row = {'timestamp': current_time, 'name': NAME}

            # Add sensor data, defaulting to an empty string if missing.
            for key in headers:
                if key in ['timestamp', 'name']:
                    continue
                row[key] = averaged_data.get(key, '')

            # Append the row to the CSV
            with open(OUTPUT_CSV, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writerow(row)

            print(f"Data logged at {current_time}")

            # Debug output for pm02Compensated
            if 'pm02Compensated' in averaged_data:
                pm_samples = []
                for ts, data in raw_samples:
                    val = data.get('pm02Compensated')
                    if val is not None:
                        try:
                            num_val = float(val)
                            pm_samples.append((ts, num_val))
                        except (ValueError, TypeError):
                            pass  # Skip non-numeric values
                if pm_samples:
                    print("\n=== DEBUG: pm02Compensated Samples and Calculation ===")
                    print("Collected Samples (Timestamp and Value):")
                    for ts, val in pm_samples:
                        print(f"  {ts}: {val}")
                    numeric_values = [val for ts, val in pm_samples]
                    count = len(numeric_values)
                    print(f"\nProcessing {count} numeric samples:")
                    if count >= 3:
                        sorted_values = sorted(numeric_values)
                        print(f"Sorted Values: {sorted_values}")
                        trimmed = sorted_values[1:-1]
                        print(f"Trimming highest and lowest: {trimmed}")
                        avg = sum(trimmed) / len(trimmed)
                    else:
                        avg = sum(numeric_values) / count
                        print(f"Using all values: {numeric_values}")
                    rounded = round(avg, 2)
                    print(f"Average: {avg} => Rounded: {rounded}")
                    print(f"Final pm02Compensated value stored: {averaged_data['pm02Compensated']}\n")

            # Calculate remaining time and sleep if needed.
            elapsed_time = time.time() - start_time
            remaining_time = INTERVAL - elapsed_time
            if remaining_time > 0:
                time.sleep(remaining_time)
            else:
                print("Warning: Sampling took longer than the interval. Proceeding immediately.")

        except Exception as e:
            print(f"Unexpected error: {e}")
            # Sleep a bit to avoid a tight loop on repeated errors.
            time.sleep(10)

if __name__ == '__main__':
    main()
