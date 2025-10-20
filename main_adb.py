import time
import subprocess
import sys
import json
from utils.adb_screenshot import run_adb_command, get_screen_size, load_config
from core.execute_adb import career_lobby

def check_adb_connection():
    """Check if ADB is connected to a device"""
    config = load_config()
    adb_path = config.get('adb_path', 'adb')
    device_address = config.get('device_address', '')
    
    def _try_connect_and_check(adb_path, device_address):
        """Helper to attempt connection and check for devices."""
        if not device_address:
            print("No device address configured in config.json (adb_config.device_address).")
            return False

        print(f"Attempting to connect to: {device_address}")
        try:
            connect_result = subprocess.run(
                [adb_path, 'connect', device_address], capture_output=True, text=True, check=False, timeout=10
            )
            output = (connect_result.stdout or '').strip()
            error_output = (connect_result.stderr or '').strip()
            if output:
                print(output)
            if error_output and not output:
                print(error_output)

            # Re-check devices after attempting to connect
            result = subprocess.run([adb_path, 'devices'], capture_output=True, text=True, check=True, timeout=10)
            lines = result.stdout.strip().split('\n')[1:]
            connected_devices = [line for line in lines if line.strip() and '\tdevice' in line]
            return bool(connected_devices)

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Error during ADB operation: {e}")
            return False

    try:
        result = subprocess.run([adb_path, 'devices'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:]  # Skip header line
        connected_devices = [line for line in lines if line.strip() and '\tdevice' in line]
        
        if not connected_devices:
            print("No ADB devices connected!")
            if not _try_connect_and_check(adb_path, device_address):
                print("\nInitial connection failed. Restarting ADB server and retrying...")
                try:
                    subprocess.run([adb_path, 'kill-server'], check=True, capture_output=True, timeout=10)
                    print("ADB server stopped.")
                    time.sleep(1)
                    subprocess.run([adb_path, 'start-server'], check=True, capture_output=True, timeout=10)
                    print("ADB server started.")
                    time.sleep(2)
                except Exception as e:
                    print(f"Failed to restart ADB server: {e}")
                    return False
                
                if not _try_connect_and_check(adb_path, device_address):
                    print(f"\nFailed to connect to device at: {device_address} after restarting server.")
                    print("Please ensure the emulator/device is running and USB debugging is enabled.")
                    print("You can also run 'python setup_adb.py' to configure the connection.")
                    return False
        
        print("Connected devices: " + str(len(connected_devices)))
        for device in connected_devices:
            print("  " + device.split('\t')[0])
        return True
        
    except subprocess.CalledProcessError:
        print("ADB command failed! Please ensure ADB is installed and in your system's PATH.")
        return False
    except FileNotFoundError:
        print("ADB not found! Please install Android SDK and add ADB to your PATH.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during ADB check: {e}")
        return False

def get_device_info():
    """Get device information"""
    try:
        # Get screen size
        width, height = get_screen_size()
        print("Device screen size: " + str(width) + "x" + str(height))
        
        # Get device model
        model = run_adb_command(['shell', 'getprop', 'ro.product.model'])
        if model:
            print("Device model: " + model)
        
        # Get Android version
        version = run_adb_command(['shell', 'getprop', 'ro.build.version.release'])
        if version:
            print("Android version: " + version)
            
        return True
        
    except Exception as e:
        print("Error getting device info: " + str(e))
        return False

def main():
    print("Uma Auto - ADB Version!")
    print("=" * 40)
    
    # Check ADB connection
    if not check_adb_connection():
        # Add a final prompt for the user
        print("\nCould not establish ADB connection. Exiting.")
        if sys.platform == "win32":
            os.system("pause") # Keep window open on Windows
        sys.exit(1)
    
    # Get device information
    if not get_device_info():
        return
    
    print("\nStarting automation...")
    print("Make sure Umamusume is running on your device!")
    print("Press Ctrl+C to stop the automation.")
    print("=" * 40)
    
    try:
        career_lobby()
    except KeyboardInterrupt:
        print("\nAutomation stopped by user.")
    except Exception as e:
        print("\nAutomation error: " + str(e))

if __name__ == "__main__":
    main() 