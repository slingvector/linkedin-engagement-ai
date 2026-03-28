#!/usr/bin/env python3
import time
import subprocess
import os
import sys
import signal
from pathlib import Path

# Add apps/core_api to path for ADBClient
sys.path.append(os.path.join(os.getcwd(), "apps", "core_api"))
from app.services.adb_client import ADBClient

LINKEDIN_PACKAGE = "com.linkedin.android"
POLL_INTERVAL = 2.0 # seconds

def main():
    print("🕵️ Lifecycle Monitor Started. Waiting for LinkedIn to open...")
    adb = ADBClient() # Uses the singleton instance
    
    recording_proc = None
    session_dir = None
    recording_name = "linkedin_manual_flow"
    
    try:
        while True:
            foreground = adb.get_foreground_package()
            
            # 1. Trigger Recording on Open
            if foreground == LINKEDIN_PACKAGE and not recording_proc:
                print(f"🚀 LinkedIn detected! Starting recording: {recording_name}")
                # Start record_flow.py in a new process group so we can SIGINT it later
                recording_proc = subprocess.Popen(
                    [sys.executable, "others/record_flow.py", recording_name, "--package", LINKEDIN_PACKAGE],
                    preexec_fn=os.setsid
                )
                # Wait for record_flow to create the session directory
                time.sleep(5)
                # Find the latest session directory in recordings/
                recordings_path = Path("recordings")
                if recordings_path.exists():
                    sessions = sorted([d for d in recordings_path.iterdir() if d.is_dir()], key=os.path.getmtime)
                    if sessions:
                        session_dir = sessions[-1]
                        print(f"📂 Active session directory: {session_dir}")

            # 2. Trigger Analysis on Close
            elif foreground != LINKEDIN_PACKAGE and recording_proc:
                # App closed or switched
                print(f"🛑 LinkedIn closed. Stopping recording and starting analysis...")
                
                # Send SIGINT to the recording process group
                os.killpg(os.getpgid(recording_proc.pid), signal.SIGINT)
                recording_proc.wait()
                recording_proc = None
                
                if session_dir and session_dir.exists():
                    print(f"📊 Starting Vision + Touch analysis for {session_dir}...")
                    analysis_proc = subprocess.Popen(
                        [sys.executable, "others/analyze_flow.py", str(session_dir)]
                    )
                    analysis_proc.wait()
                    print(f"✅ Analysis complete for {session_dir}")
                    print("\n" + "="*50)
                    print("🕵️ Monitoring for next LinkedIn launch...")
                    print("="*50 + "\n")
                else:
                    print("⚠️ Could not find session directory for analysis.")
            
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nStopping Lifecycle Monitor...")
        if recording_proc:
            os.killpg(os.getpgid(recording_proc.pid), signal.SIGINT)
            recording_proc.wait()

if __name__ == "__main__":
    main()
