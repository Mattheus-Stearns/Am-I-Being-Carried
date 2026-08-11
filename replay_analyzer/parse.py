# parse.py
import subprocess
import json
import os
import platform

def parse_replay_to_dict(replay_path):
    """Parses a replay using an OS-specific rrrocket binary with absolute paths."""
    
    # 1. Clean path and resolve to an absolute system path
    clean_replay = str(replay_path).replace('\x00', '').strip()
    abs_replay_path = os.path.abspath(clean_replay)
    
    # 2. Get the exact folder where parse.py lives
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    current_os = platform.system().lower()
    
    # 3. Build absolute path directly to the binary file
    if current_os == "windows":
        binary_path = os.path.join(base_dir, "windows", "rrrocket.exe")
    elif current_os == "darwin": # macOS
        binary_path = os.path.join(base_dir, "mac", "rrrocket")
        current_os = "macOS"
    elif current_os == "linux":
        binary_path = os.path.join(base_dir, "linux", "rrrocket")
    else:
        print(f"Unsupported OS: {current_os}")
        return None

    # 4. Safety check: Verify the binary actually exists
    if not os.path.exists(binary_path):
        print(f"Error: Executable not found at target: {binary_path}")
        return None

    # 5. Assemble the precise execution command array
    command = [binary_path, "-n", abs_replay_path]
    
    try:
        # Run subprocess using the full path to the executable file
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            print("Parsing failed. Native CLI Error:")
            print(result.stderr)
            return None
            
    except Exception as e:
        print(f"Execution failed to launch process: {e}")
        print(f"Attempted command array was: {command}")
        return None
