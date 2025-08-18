#!/usr/bin/env python3

import sys
import json
from zmqhelper import Client

def test_zmq_connection():
    """Test direct ZMQ connection to debug issues"""
    
    print("🔍 Testing ZMQ Connection to [ZMQ_HOST]:5100")
    print("=" * 60)
    
    try:
        # Create client - use environment variable or config
        import os
        zmq_host = os.getenv('ZMQ_HOST', 'localhost')
        client = Client(ip=zmq_host, port=5100)
        print("✅ ZMQ Client created successfully")
        
        # Test basic connection with 'test' command
        print("\n1. Testing 'test' command...")
        message = json.dumps({"cmd": "test", "params": {}})
        print(f"   Sending: {message}")
        
        response = client.send_message(message, timeout=5000)  # 5 second timeout
        print(f"   Raw response: {repr(response)}")
        
        if response and response.strip():
            try:
                parsed = json.loads(response)
                print(f"   Parsed response: {parsed}")
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON decode error: {e}")
        else:
            print("   ❌ Empty or None response")
        
        # Test 'info' command to get paths
        print("\n2. Testing 'info' command...")
        message = json.dumps({"cmd": "info", "params": {}})
        print(f"   Sending: {message}")
        
        response = client.send_message(message, timeout=5000)
        print(f"   Raw response: {repr(response[:200])}..." if len(response) > 200 else f"   Raw response: {repr(response)}")
        
        if response and response.strip():
            try:
                parsed = json.loads(response)
                print(f"   Status: {parsed.get('message', {}).get('status', 'Unknown')}")
                settings = parsed.get('message', {}).get('settings', {})
                print(f"   Available paths: {list(settings.keys())}")
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON decode error: {e}")
        else:
            print("   ❌ Empty or None response")
        
        # Test 'commands' command
        print("\n3. Testing 'commands' command...")
        message = json.dumps({"cmd": "commands", "params": {}})
        print(f"   Sending: {message}")
        
        response = client.send_message(message, timeout=5000)
        print(f"   Raw response length: {len(response) if response else 0}")
        
        if response and response.strip():
            try:
                parsed = json.loads(response)
                commands = parsed.get('message', {})
                print(f"   Available commands: {len(commands)} commands found")
                for key, cmd_info in list(commands.items())[:3]:  # Show first 3
                    print(f"     {key}: {cmd_info.get('cmd', 'Unknown')}")
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON decode error: {e}")
        else:
            print("   ❌ Empty or None response")
            
        print("\n✅ ZMQ connection test completed")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_zmq_connection()