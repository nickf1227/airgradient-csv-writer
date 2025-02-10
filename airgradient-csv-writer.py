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
    
    This approach ensures that the CSV file is correctly formatted and ready to store data.
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
    Get multiple samples from the sensor API.
    
    This function collects a specified number of samples from the sensor API,
    with a delay between each sample. This approach is necessary because the
    sensor readings can vary significantly over short periods, as shown in the example:
    
    2025-02-09 13:08:01 pm02Compensated: 948.89
    2025-02-09 13:08:04 pm02Compensated: 1136.21
    2025-02-09 13:08:07 pm02Compensated: 1264.21
    2025-02-09 13:08:10 pm02Compensated: 1334.69
    2025-02-09 13:08:13 pm02Compensated: 1279.43
    2025-02-09 13:08:16 pm02Compensated: 1087.97
    2025-02-09 13:08:20 pm02Compensated: 980.06
    2025-02-09 13:08:23 pm02Compensated: 771.77
    2025-02-09 13:08:26 pm02Compensated: 681.78
    2025-02-09 13:08:29 pm02Compensated: 526.86
    2025-02-09 13:08:32 pm02Compensated: 459.74
    2025-02-09 13:08:35 pm02Compensated: 340.83
    2025-02-09 13:08:38 pm02Compensated: 293.2
    2025-02-09 13:08:41 pm02Compensated: 200.2
    2025-02-09 13:08:44 pm02Compensated: 162.82
    2025-02-09 13:08:47 pm02Compensated: 123.25
    2025-02-09 13:08:50 pm02Compensated: 107.01
    2025-02-09 13:08:53 pm02Compensated: 81.47
    2025-02-09 13:08:56 pm02Compensated: 62.87
    2025-02-09 13:08:59 pm02Compensated: 55.92
    
    By taking multiple samples and averaging them, we can obtain a more stable and accurate reading.
    """
    samples = []
    for _ in range(num_samples):
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            samples.append(data)
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        time.sleep(sample_interval)
    return samples

def average_samples(samples):
    """
    Average the samples, discarding the highest and lowest values.
    
    This approach helps to mitigate the impact of outliers and provides a more
    accurate representation of the sensor data. If there are fewer than 3 samples,
    an error is raised.
    """
    if len(samples) < 3:
        raise ValueError("Not enough samples to average")

    averaged_data = {}
    for key in samples[0].keys():
        values = [sample[key] for sample in samples if key in sample]
        if len(values) < 3:
            continue
        values.sort()
        values = values[1:-1]  # Discard the highest and lowest values
        averaged_data[key] = sum(values) / len(values)
    return averaged_data

def main():
    headers = initialize_csv(URL, OUTPUT_CSV)

    # Main collection loop: query the sensor API and log data continuously.
    while True:
        try:
            samples = get_samples(URL, SAMPLES_PER_INTERVAL, SAMPLE_INTERVAL)
            if len(samples) < SAMPLES_PER_INTERVAL:
                print("Not enough samples collected; skipping entry.")
                time.sleep(INTERVAL)
                continue

            averaged_data = average_samples(samples)
            current_time = datetime.now().isoformat()

            # Prepare the row with the configured timestamp and name.
            row = {'timestamp': current_time, 'name': NAME}

            # Validate and add sensor data for each expected field.
            for key in headers:
                if key in ['timestamp', 'name']:
                    continue
                row[key] = averaged_data.get(key, '')

            # Append the row to the CSV.
            with open(OUTPUT_CSV, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writerow(row)

            print(f"Data logged at {current_time}")

        except Exception as e:
            print(f"Unexpected error: {e}")

        # Wait for the next interval.
        time.sleep(INTERVAL - (SAMPLES_PER_INTERVAL * SAMPLE_INTERVAL))

if __name__ == '__main__':
    main()
