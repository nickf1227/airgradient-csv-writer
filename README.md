# airgradient-csv-writer

This Python script continuously queries a sensor API and logs the returned data to a CSV file. The CSV file is automatically initialized with headers based on the sensor response, ensuring that:

- The **first column** is a timestamp (in ISO8601 format).
- If available, the **second column** is the sensor's `serialno`.
- All other sensor data fields are sorted alphabetically.

> **Note:** The script only logs the fields present during the initial API request. If new fields are added later by the API, they will be ignored. To update the schema, delete the existing CSV file before running the script again.

## Features

- **Hard-coded configuration:** Set the sensor API URL, output CSV file path, and query interval directly in the script.
- **Automatic CSV initialization:** The CSV file is created with the appropriate headers based on the initial sensor response.
- **Consistent column ordering:** The CSV always starts with `timestamp` (and `serialno` if available), followed by the rest of the sensor fields in alphabetical order.
- **Continuous logging:** The script continuously queries the sensor API and appends new data rows until interrupted.

## Requirements

- **Python:** 3.6 or later

## Configuration

All configuration settings are defined at the top of the script. Modify these variables as needed:

- **`URL`**: The sensor API endpoint (e.g., `http://10.69.10.92/measures/current`).
- **`OUTPUT_CSV`**: The file path for the CSV output (e.g., `data.csv`).
- **`INTERVAL`**: The time (in seconds) between successive API queries (e.g., `60`).

## Usage

Simply run the script using Python

When executed, the script will:

1. **Initialize the CSV File:**  
   - If the file does not exist, the script will query the sensor API to determine the schema, create the CSV file with the correct headers, and write the first row.
   - If the file already exists, it will continue appending new data rows using the existing header structure.

2. **Log Sensor Data:**  
   The script queries the sensor API every `INTERVAL` seconds. Each successful query writes a new row to the CSV file containing the current timestamp and the sensor data.

## CSV Output Format

The CSV file columns are organized as follows:

- **timestamp**: The date and time when the data was logged (ISO8601 format).
- **serialno**: The sensor's serial number (if present).
- **Other Sensor Fields:** Sorted alphabetically.

Example CSV header:

```
timestamp,serialno,atmp,atmpCompensated,boot,bootCount,firmware,ledMode,model,noxIndex,noxRaw,pm003Count,pm005Count,pm01,pm01Count,pm01Standard,pm02,pm02Compensated,pm02Count,pm02Standard,pm10,pm10Count,pm10Standard,pm50Count,rco2,rhum,rhumCompensated,tvocIndex,tvocRaw,wifi
```

## Error Handling

- **Missing Fields:** If an expected sensor field is missing in a given API response, that data entry is skipped.
- **CSV File Issues:** If the CSV file exists but has no headers, the script exits with an error message.
- **API Request Errors:** Any issues with the API request are printed to the console, and the script attempts to continue logging after waiting for the specified interval.

## Current compatible Schema
For most up to date information, please see here: https://github.com/airgradienthq/arduino/blob/master/docs/local-server.md
As of 2/8/2025, the schema this script is expecting is:


| Property            | Type   | Explanation                                                                                           |
|---------------------|--------|-------------------------------------------------------------------------------------------------------|
| serialno            | String | Serial Number of the monitor                                                                          |
| wifi                | Number | WiFi signal strength                                                                                  |
| pm01                | Number | PM1.0 in ug/m3 (atmospheric environment)                                                              |
| pm02                | Number | PM2.5 in ug/m3 (atmospheric environment)                                                              |
| pm10                | Number | PM10 in ug/m3 (atmospheric environment)                                                               |
| pm02Compensated     | Number | PM2.5 in ug/m3 with correction applied (from fw version 3.1.4 onwards)                                |
| pm01Standard        | Number | PM1.0 in ug/m3 (standard particle)                                                                    |
| pm02Standard        | Number | PM2.5 in ug/m3 (standard particle)                                                                    |
| pm10Standard        | Number | PM10 in ug/m3 (standard particle)                                                                     |
| rco2                | Number | CO2 in ppm                                                                                            |
| pm003Count          | Number | Particle count 0.3um per dL                                                                           |
| pm005Count          | Number | Particle count 0.5um per dL                                                                           |
| pm01Count           | Number | Particle count 1.0um per dL                                                                           |
| pm02Count           | Number | Particle count 2.5um per dL                                                                           |
| pm50Count           | Number | Particle count 5.0um per dL (only for indoor monitor)                                                 |
| pm10Count           | Number | Particle count 10um per dL (only for indoor monitor)                                                  |
| atmp                | Number | Temperature in Degrees Celsius                                                                        |
| atmpCompensated     | Number | Temperature in Degrees Celsius with correction applied                                                |
| rhum                | Number | Relative Humidity                                                                                     |
| rhumCompensated     | Number | Relative Humidity with correction applied                                                             |
| tvocIndex           | Number | Senisiron VOC Index                                                                                   |
| tvocRaw             | Number | VOC raw value                                                                                         |
| noxIndex            | Number | Senisirion NOx Index                                                                                  |
| noxRaw              | Number | NOx raw value                                                                                         |
| boot                | Number | Counts every measurement cycle. Low boot counts indicate restarts.                                    |
| bootCount           | Number | Same as boot property. Required for Home Assistant compatibility (deprecated soon!)                   |
| ledMode             | String | Current configuration of the LED mode                                                                 |
| firmware            | String | Current firmware version                                                                              |
| model               | String | Current model name                                                                                    |


## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

## Contributing

Feel free to fork this project and submit pull requests for improvements or additional features.

---

Happy logging!
```

---

You can save this content as `README.md` in your project directory. Adjust any sections as needed for your use case.
