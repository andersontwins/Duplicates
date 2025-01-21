import os
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
import logging
import json
import mmap
import subprocess
import sys

# Load configuration settings from config file
def load_config(config_file="config.json"):
    with open(config_file, 'r') as f:
        return json.load(f)

config = load_config()

# Function to install missing packages
def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {package}. Please install it manually.")
        exit(1)

# Check for pip installation
try:
    import pip
except ImportError:
    print("pip is not installed. Please install pip first.")
    exit(1)

# Check for xxhash installation
try:
    import xxhash
except ImportError:
    print("xxhash module not found. Installing...")
    install_package("xxhash")
    import xxhash

# Check for tqdm installation
try:
    from tqdm import tqdm
except ImportError:
    print("tqdm module not found. Installing...")
    install_package("tqdm")
    from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename=config['log_file'], filemode='w')

def file_hash(file_path):
    """Compute the xxHash of the given file."""
    hash_xx = xxhash.xxh64()
    try:
        with open(file_path, "rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                hash_xx.update(mm)
        return hash_xx.hexdigest()
    except Exception as e:
        logging.error(f"Error reading {file_path}: {e}")
        return None

def collect_file_info(directories, temp_file=config['temp_file']):
    """Collect file information including paths, names, hashes, and metadata."""
    file_info_dict = {}

    # Load existing progress if temp file exists
    if os.path.exists(temp_file):
        with open(temp_file, 'r') as f:
            file_info_dict = json.load(f)

    # Collect all file paths, ignoring hidden files and files in the ignore list
    file_paths = []
    for directory in directories:
        for root, _, files in os.walk(directory):
            for file in files:
                if not any(file.startswith(prefix) for prefix in config['ignore_list']):
                    file_paths.append(os.path.join(root, file))

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(file_hash, file_path): file_path for file_path in file_paths if file_path not in file_info_dict}

        with tqdm(total=len(futures), desc="Processing files", unit="file") as pbar:
            for future in as_completed(futures):
                file_path = futures[future]
                file_hash_result = future.result()
                if file_hash_result:
                    file_info = {
                        'name': os.path.basename(file_path),
                        'hash': file_hash_result,
                        'size': os.path.getsize(file_path),
                        'modified_time': os.path.getmtime(file_path)
                    }
                    file_info_dict[file_path] = file_info
                pbar.update(1)

                # Save progress periodically
                if len(file_info_dict) % config['save_interval'] == 0:
                    with open(temp_file, 'w') as f:
                        json.dump(file_info_dict, f, indent=4)

    # Save final progress
    with open(temp_file, 'w') as f:
        json.dump(file_info_dict, f, indent=4)

    return file_info_dict

def save_file_info(file_info_dict, output_file):
    """Save file information to a JSON file."""
    if os.path.isdir(output_file):
        print(f"Error: {output_file} is a directory. Saving to default file 'file_info_report.json'.")
        logging.error(f"Error: {output_file} is a directory. Saving to default file 'file_info_report.json'.")
        output_file = os.path.join(output_file, 'file_info_report.json')
    with open(output_file, 'w') as f:
        json.dump(file_info_dict, f, indent=4)

def load_file_info(input_file):
    """Load file information from a JSON file."""
    with open(input_file, 'r') as f:
        return json.load(f)

def verify_file_info(file_info_dict):
    """Verify the existence and integrity of files listed in the file information."""
    verified_file_info_dict = {}
    with tqdm(total=len(file_info_dict), desc="Verifying files", unit="file") as pbar:
        for file_path, file_info in file_info_dict.items():
            if os.path.exists(file_path):
                current_hash = file_hash(file_path)
                if current_hash == file_info['hash']:
                    verified_file_info_dict[file_path] = file_info
                else:
                    logging.warning(f"File hash changed: {file_path}")
            else:
                logging.warning(f"File not found: {file_path}")
            pbar.update(1)
    return verified_file_info_dict

def find_duplicates_from_info(file_info_dict):
    """Find duplicates based on file information."""
    hashes = {}
    duplicates = []

    for file_path, file_info in file_info_dict.items():
        file_hash_result = file_info['hash']
        if file_hash_result in hashes:
            duplicates.append((file_path, hashes[file_hash_result]))
            logging.info(f"Duplicate found: {file_path} is a duplicate of {hashes[file_hash_result]}")
        else:
            hashes[file_hash_result] = file_path

    if duplicates:
        print("Duplicates found:")
        for dup in duplicates:
            print(f"{dup[0]} is a duplicate of {dup[1]}")
    else:
        print("No duplicates found.")
    
    return duplicates

def group_duplicates_by_directory(duplicates):
    """Group duplicates by directory."""
    grouped_duplicates = {}
    for dup in duplicates:
        dir_path = os.path.dirname(dup[0])
        if dir_path not in grouped_duplicates:
            grouped_duplicates[dir_path] = []
        grouped_duplicates[dir_path].append(dup)
    return grouped_duplicates

def handle_duplicates(grouped_duplicates):
    """Prompt user for action on each duplicate file."""
    for dir_path, duplicates in grouped_duplicates.items():
        print(f"\nDirectory: {dir_path}")
        action = input("Choose action for this directory: [s]kip, [d]elete all, [m]ove all, [i]ndividual: ").strip().lower()
        
        if action == 's':
            print(f"Skipping directory: {dir_path}")
            logging.info(f"Skipping directory: {dir_path}")
            continue
        elif action == 'd':
            for dup in duplicates:
                try:
                    os.remove(dup[0])
                    print(f"Deleted {dup[0]}")
                    logging.info(f"Deleted {dup[0]}")
                except Exception as e:
                    print(f"Error deleting file {dup[0]}: {e}")
                    logging.error(f"Error deleting file {dup[0]}: {e}")
        elif action == 'm':
            target_directory = input("Enter target directory for moving: ").strip()
            if not os.path.exists(target_directory):
                os.makedirs(target_directory)
            for dup in duplicates:
                try:
                    shutil.move(dup[0], target_directory)
                    print(f"Moved {dup[0]} to {target_directory}")
                    logging.info(f"Moved {dup[0]} to {target_directory}")
                except Exception as e:
                    print(f"Error moving file {dup[0]}: {e}")
                    logging.error(f"Error moving file {dup[0]}: {e}")
        elif action == 'i':
            for dup in duplicates:
                print(f"\nDuplicate found:\n1. {dup[0]}\n2. {dup[1]}")
                individual_action = input("Choose action: [k]eep both, [d]elete first, [D]elete second, [m]ove first, [M]ove second: ").strip().lower()
                
                if individual_action == 'd':
                    try:
                        os.remove(dup[0])
                        print(f"Deleted {dup[0]}")
                        logging.info(f"Deleted {dup[0]}")
                    except Exception as e:
                        print(f"Error deleting {dup[0]}: {e}")
                        logging.error(f"Error deleting {dup[0]}: {e}")
                elif individual_action == 'd':
                    try:
                        os.remove(dup[1])
                        print(f"Deleted {dup[1]}")
                        logging.info(f"Deleted {dup[1]}")
                    except Exception as e:
                        print(f"Error deleting {dup[1]}: {e}")
                        logging.error(f"Error deleting {dup[1]}: {e}")
                elif individual_action == 'm':
                    target_directory = input("Enter target directory for moving: ").strip()
                    if not os.path.exists(target_directory):
                        os.makedirs(target_directory)
                    try:
                        shutil.move(dup[0], target_directory)
                        print(f"Moved {dup[0]} to {target_directory}")
                        logging.info(f"Moved {dup[0]} to {target_directory}")
                    except Exception as e:
                        print(f"Error moving {dup[0]}: {e}")
                        logging.error(f"Error moving {dup[0]}: {e}")
                elif individual_action == 'm':
                    target_directory = input("Enter target directory for moving: ").strip()
                    if not os.path.exists(target_directory):
                        os.makedirs(target_directory)
                    try:
                        shutil.move(dup[1], target_directory)
                        print(f"Moved {dup[1]} to {target_directory}")
                        logging.info(f"Moved {dup[1]} to {target_directory}")
                    except Exception as e:
                        print(f"Error moving {dup[1]}: {e}")
                        logging.error(f"Error moving {dup[1]}: {e}")
                else:
                    print("Keeping both files.")
                    logging.info(f"Keeping both files: {dup[0]} and {dup[1]}")
        else:
            print("Invalid action. Skipping directory.")
            logging.info(f"Invalid action. Skipping directory: {dir_path}")

if __name__ == "__main__":
    directories = config['directories']
    if all(os.path.isdir(directory) for directory in directories):
        use_existing_report = input("Do you have an existing report file to load? (y/n): ").strip().lower()
        if use_existing_report == 'y':
            report_file = input("Enter the path to the report file: ").strip()
            if os.path.isfile(report_file):
                file_info_dict = load_file_info(report_file)
                print("Loaded file information from report.")
                file_info_dict = verify_file_info(file_info_dict)
                save_file_info(file_info_dict, report_file)  # Update the report file with verified info
                print("Verified and updated file information.")
            else:
                print(f"Invalid report file: {report_file}")
                logging.error(f"Invalid report file: {report_file}")
                exit(1)
        else:
            file_info_dict = collect_file_info(directories)
            report_file = input("Enter the path to save the report file: ").strip()
            save_file_info(file_info_dict, report_file)
            print(f"File information saved to {report_file}")

        duplicates = find_duplicates_from_info(file_info_dict)
        grouped_duplicates = group_duplicates_by_directory(duplicates)
        handle_duplicates(grouped_duplicates)
    else:
        print(f"Invalid directories: {directories}")
        logging.error(f"Invalid directories: {directories}")