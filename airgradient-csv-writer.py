import requests
import csv
import time
from datetime import datetime
import os

# ========================
# User Configuration
# ========================
URL = "http://10.69.10.92/measures/current"  # Sensor API URL
OUTPUT_CSV = "./airgradient.csv"                      # Output CSV file path
INTERVAL = 60                                # Interval in seconds between queries
NAME = "MySensorName"                        # Custom name to include in CSV

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

def main():
    headers = initialize_csv(URL, OUTPUT_CSV)

    # Main collection loop: query the sensor API and log data continuously.
    while True:
        try:
            response = requests.get(URL)
            response.raise_for_status()
            data = response.json()
            current_time = datetime.now().isoformat()

            # Prepare the row with the configured timestamp and name.
            row = {'timestamp': current_time, 'name': NAME}

            # Validate and add sensor data for each expected field.
            missing_field = False
            for key in headers:
                if key in ['timestamp', 'name']:
                    continue
                if key not in data:
                    print(f"Missing field '{key}' in sensor response; skipping entry.")
                    missing_field = True
                    break
                row[key] = data[key]
            if missing_field:
                time.sleep(INTERVAL)
                continue

            # Append the row to the CSV.
            with open(OUTPUT_CSV, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writerow(row)

            print(f"Data logged at {current_time}")

        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

        # Wait for the next interval.
        time.sleep(INTERVAL)

if __name__ == '__main__':
    main()
