import argparse
import contextlib
import sys
import io
from parse import parse_replay_to_dict
from dataframe import build_telemetry_dataframe
import carball
import json
from graph import plot_player_speeds, plot_boost_usage, calculate_advanced_boost_stats
from datetime import datetime

parser = argparse.ArgumentParser(description="A simple python library to analyze rocket league replays.")

parser.add_argument("-f", "--files", type=str, nargs="+", help="location of your replay file")
parser.add_argument("-o", "--output", type=str, nargs="?", default="analysis.txt", help="the file where the analysis should be written")
parser.add_argument("-l", "--log", type=str, nargs="?", default="log.txt", help="the file where the log should be written")
parser.add_argument("-v", "--verbose", action="store_true", help="toggle verbose output")

if len(sys.argv) == 1:
    parser.print_help(sys.stderr)
    sys.exit(1)

args = parser.parse_args()

parsed_data = []

for file in args.files:
    if file is None:
        parser.print_help(sys.stderr)
        parser.error("Error: The --file argument is required.")

    if not file.endswith(".replay"):
        parser.print_help(sys.stderr)
        parser.error(f"Error {file}: The --file argument needs to end in .replay")

    if args.verbose:
        print(f"Recieved your {file}, parsing it.")

    parsed_data.append(parse_replay_to_dict(file))

print("Using your OS to parse your replay file according to the specific parser.")


with open(".data.json", "w") as f:
    for i in parsed_data:
        json.dump(i, f, indent=4)

count = 0

try:
    for data in parsed_data:
        frames = data.get("network_frames", {}).get("frames", [])

        if frames:
            print(f"Extracted {len(frames)} frames of data from dataframe {count + 1}.")
        else:
            print(f"Warning: No frame data found from dataframe {count + 1}. Make sure it's a full match replay.")

        count += 1

except Exception as e:
    print(f"An unexpected error occurred: {e}")
    sys.exit(2)

def run_parser_with_logging(parsed_data, log_file_path, replay_date):
    """
    Run the parser and capture all print output to a file (no console output).
    """
    
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        with contextlib.redirect_stdout(log_file):
            # All prints will go ONLY to the log file
            df = build_telemetry_dataframe(parsed_data, replay_date)
    
    print(f"✅ Parser output logged to: {log_file_path}")
    return df

def run_plot_with_logging(df_telemetry, log_file_path, replay_date):
    """
        Make the plot and capture all print output to a file (no console output).
    """
    with open(log_file_path, 'a', encoding='utf-8') as log_file:
            with contextlib.redirect_stdout(log_file):
                player_speeds = plot_player_speeds(df_telemetry, replay_date)
                boost_usage = plot_boost_usage(df_telemetry, replay_date)

    print(f"✅ Plot debug output logged to: {log_file_path}")
    return df_telemetry

def parse_replay_date(replay_data):
    """
    Extract and parse the replay date from the properties section.
    Returns a datetime object and formatted string.
    """
    # Navigate to the properties section
    properties = replay_data.get("properties", {})
    
    # Get the date string
    date_str = properties.get("Date", "")
    
    if not date_str:
        print("⚠️ No date found in replay data")
        return None, None
    
    print(f"📅 Raw date string: {date_str}")
    
    # The date format appears to be: "2026-07-29 04-31-41"
    # Convert hyphens in time part to colons for proper parsing
    # Replace the second and third hyphens with colons
    parts = date_str.split()
    if len(parts) == 2:
        date_part = parts[0]  # "2026-07-29"
        time_part = parts[1]  # "04-31-41"
        
        # Convert time part from "04-31-41" to "04:31:41"
        time_part_fixed = time_part.replace('-', ':')
        date_str_fixed = f"{date_part} {time_part_fixed}"
    else:
        date_str_fixed = date_str
    
    try:
        # Parse the date
        dt = datetime.strptime(date_str_fixed, "%Y-%m-%d %H:%M:%S")
        
        # Format for display
        human_readable = dt.strftime("%B %d, %Y at %I:%M:%S %p")
        
        return dt, human_readable
        
    except ValueError as e:
        print(f"⚠️ Error parsing date: {e}")
        return None, None

for data in parsed_data:
    dt, human_readable = parse_replay_date(data)
    dt = dt.strftime('%Y-%m-%d %H:%M:%S').replace(' ', '_')
    df_telemetry = run_parser_with_logging(data, args.log, dt)
    plot = run_plot_with_logging(df_telemetry, args.log, dt)

    with open(args.output, 'w', encoding='utf-8') as out:
        out.writelines(calculate_advanced_boost_stats(df_telemetry))
