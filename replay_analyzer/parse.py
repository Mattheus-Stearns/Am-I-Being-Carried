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
    
    print(f"🔍 Parsing replay: {abs_replay_path}")
    print(f"📁 File exists: {os.path.exists(abs_replay_path)}")
    
    # 2. Get the exact folder where parse.py lives
    base_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"📁 Base directory: {base_dir}")
    
    current_os = platform.system().lower()
    print(f"🖥️ Operating System: {current_os}")
    
    # 3. Build absolute path directly to the binary file
    if current_os == "windows":
        binary_path = os.path.join(base_dir, "windows", "rrrocket.exe")
    elif current_os == "darwin":  # macOS
        binary_path = os.path.join(base_dir, "mac", "rrrocket")
        current_os = "macOS"
    elif current_os == "linux":
        binary_path = os.path.join(base_dir, "linux", "rrrocket")
    else:
        print(f"❌ Unsupported OS: {current_os}")
        return None

    print(f"📁 Binary path: {binary_path}")
    print(f"📁 Binary exists: {os.path.exists(binary_path)}")
    
    # 4. Check if the binary exists and is executable
    if not os.path.exists(binary_path):
        print(f"❌ Error: Executable not found at: {binary_path}")
        
        # Try to find it in other locations
        possible_paths = [
            os.path.join(base_dir, "..", "rrrocket", "rrrocket"),
            os.path.join(base_dir, "..", "rrrocket", "linux", "rrrocket"),
            "/usr/local/bin/rrrocket",
            "/usr/bin/rrrocket"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"✅ Found rrrocket at: {path}")
                binary_path = path
                break
        
        if not os.path.exists(binary_path):
            print("❌ Could not find rrrocket binary anywhere!")
            return None

    # 5. Make sure the binary is executable
    if not os.access(binary_path, os.X_OK):
        print(f"🔧 Making binary executable: {binary_path}")
        try:
            os.chmod(binary_path, 0o755)
        except Exception as e:
            print(f"❌ Could not make binary executable: {e}")

    # 6. Assemble the precise execution command array
    command = [binary_path, "-n", abs_replay_path]
    print(f"🔧 Command: {' '.join(command)}")
    
    try:
        # Run subprocess using the full path to the executable file
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        
        print(f"📊 Return code: {result.returncode}")
        
        if result.returncode == 0:
            try:
                parsed_data = json.loads(result.stdout)
                print(f"✅ Successfully parsed replay: {len(str(parsed_data))} bytes")
                return parsed_data
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
                print(f"📄 Output preview: {result.stdout[:500]}")
                return None
        else:
            print("❌ Parsing failed. Native CLI Error:")
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout[:500]}")
            return None
            
    except subprocess.TimeoutExpired:
        print("❌ Parsing timed out after 60 seconds")
        return None
    except Exception as e:
        print(f"❌ Execution failed to launch process: {e}")
        print(f"Attempted command array was: {command}")
        return None