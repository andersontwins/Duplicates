# Duplicates

## Description
Duplicates is a tool designed to help you identify and manage duplicate files within a specified directory. It scans the directory, compares files based on their content, and provides options to handle the duplicates.

## Installation
To install the required dependencies, run:
```sh
pip install -r requirements.txt
```

## Configuration

The tool uses a configuration file to set various options. The default configuration file is

config.json

. Here is an example of what it might look like:

```json
{
    "scan_directory": "/path/to/scan",
    "report_file": "duplicates_report.txt",
    "temp_file": "temp_duplicates.txt",
    "delete_duplicates": false
}
```

- `scan_directory`: The directory to scan for duplicates.
- `report_file`: The file where the report of duplicates will be saved.
- `temp_file`: A temporary file used during the scanning process.
- `delete_duplicates`: A boolean flag to indicate whether duplicates should be automatically deleted.

## Usage

To use the Duplicates tool, follow these steps:

1. **Navigate to the project directory**:

   ```sh
   cd /path/to/Duplicates
   ```

2. **Run the script**:

   ```sh
   python duplicates.py /path/to/config.json
   ```

   Replace `/path/to/config.json` with the path to your configuration file.

3. **Options**:
   - You can add various command-line options to customize the behavior of the tool. For example:

     ```sh
     python duplicates.py /path/to/config.json --delete
     ```

     This will automatically delete the duplicate files found based on the configuration.

## How Duplicates are Found and Managed

1. **Scanning**: The tool scans the specified directory and reads the files.
2. **Comparison**: It compares files based on their content using a hashing algorithm to detect duplicates.
3. **Reporting**: A report is generated and saved to the specified report file (`duplicates_report.txt`).
4. **Temporary File**: A temporary file (`temp_duplicates.txt`) is used during the scanning process to store intermediate results.
5. **Managing Duplicates**: Based on the configuration, duplicates can either be listed in the report or automatically deleted if the `delete_duplicates` flag is set to `true`.

## Contributing

If you would like to contribute to this project, please follow these steps:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Commit your changes (`git commit -m 'Add some feature'`).
5. Push to the branch (`git push origin feature-branch`).
6. Open a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

If you have any questions or suggestions, feel free to open an issue or contact me directly at [coryanderson@fullsail.edu].

```

## Additional Information

