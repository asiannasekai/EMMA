#!/usr/bin/env python3
"""
EMMA UE Simulator - Simulates a mobile device receiving emergency alerts
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime

class EmmaUESimulator:
    def __init__(self, ue_id, location=None):
        self.ue_id = ue_id
        self.location = location or {"lat": 40.7128, "lon": -74.0060}  # Default to NYC
        self.ws = None
        
    async def connect_to_emma(self, uri="ws://localhost:8080"):
        """Connect to EMMA Alert Distributor WebSocket"""
        try:
            print(f"📱 UE {self.ue_id} connecting to EMMA system...")
            self.ws = await websockets.connect(uri)
            
            # Register with the system
            registration = {
                "type": "register_ue",
                "ue_id": self.ue_id,
                "location": self.location,
                "capabilities": ["CAP", "multimedia", "evacuation_maps"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.ws.send(json.dumps(registration))
            print(f"✅ UE {self.ue_id} registered successfully")
            
            # Listen for alerts
            await self.listen_for_alerts()
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            
    async def listen_for_alerts(self):
        """Listen for incoming emergency alerts"""
        print(f"👂 UE {self.ue_id} listening for emergency alerts...")
        
        try:
            async for message in self.ws:
                alert_data = json.loads(message)
                await self.handle_alert(alert_data)
                
        except websockets.exceptions.ConnectionClosed:
            print(f"📱 UE {self.ue_id} connection closed")
        except Exception as e:
            print(f"❌ Error receiving alerts: {e}")
            
    async def handle_alert(self, alert_data):
        """Process incoming emergency alert"""
        print("\n" + "="*60)
        print("🚨 EMERGENCY ALERT RECEIVED 🚨")
        print("="*60)
        
        alert_type = alert_data.get("type", "unknown")
        
        if alert_type == "alert":
            # Display alert information
            print(f"📱 UE ID: {self.ue_id}")
            print(f"🆔 Alert ID: {alert_data.get('id', 'N/A')}")
            print(f"⚡ Urgency: {alert_data.get('urgency', 'N/A')}")
            print(f"🔴 Severity: {alert_data.get('severity', 'N/A')}")
            print(f"📢 Event: {alert_data.get('event', 'N/A')}")
            print(f"📰 Headline: {alert_data.get('headline', 'N/A')}")
            print(f"📝 Description: {alert_data.get('description', 'N/A')}")
            print(f"📍 Area: {alert_data.get('area', 'N/A')}")
            print(f"⏰ Expires: {alert_data.get('expires', 'N/A')}")
            
            # Display multimedia content URLs
            if alert_data.get('mediaUrl'):
                print(f"🖼️  Alert Image: {alert_data['mediaUrl']}")
            if alert_data.get('evacuationMap'):
                print(f"🗺️  Evacuation Map: {alert_data['evacuationMap']}")
            if alert_data.get('audioAlert'):
                print(f"🎵 Audio/Video: {alert_data['audioAlert']}")
                
            print(f"⏰ Received at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            # Simulate user action
            await self.simulate_user_response(alert_data)
            
        elif alert_type == "registration_confirmed":
            print(f"✅ Registration confirmed for UE {self.ue_id}")
            
        elif alert_type == "heartbeat":
            print(f"💓 Heartbeat from EMMA system")
            
        else:
            print(f"📩 Received message type: {alert_type}")
            print(f"📄 Data: {json.dumps(alert_data, indent=2)}")
            
    async def simulate_user_response(self, alert_data):
        """Simulate user interaction with the alert"""
        print("\n📱 User Actions Available:")
        print("1. ✅ Acknowledge alert")
        print("2. 📍 Update location")
        print("3. 🆘 Request assistance")
        print("4. 🔇 Mute alerts (not recommended)")
        
        # Auto-acknowledge after a delay
        await asyncio.sleep(2)
        
        response = {
            "type": "alert_response",
            "ue_id": self.ue_id,
            "alert_id": alert_data.get('id'),
            "action": "acknowledged",
            "location": self.location,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            await self.ws.send(json.dumps(response))
            print("✅ Alert acknowledged automatically")
        except Exception as e:
            print(f"❌ Failed to send acknowledgment: {e}")

async def main():
    """Run UE simulator"""
    if len(sys.argv) > 1:
        ue_id = sys.argv[1]
    else:
        ue_id = "UE-SIM-001"
        
    # Create UE simulator
    simulator = EmmaUESimulator(
        ue_id=ue_id,
        location={"lat": 40.7589, "lon": -73.9851, "address": "Times Square, NYC"}
    )
    
    print("🚨 EMMA UE Emergency Alert Simulator 🚨")
    print(f"Starting simulation for UE: {ue_id}")
    print("Press Ctrl+C to stop")
    
    try:
        await simulator.connect_to_emma()
    except KeyboardInterrupt:
        print(f"\n👋 UE {ue_id} simulator stopped")
    except Exception as e:
        print(f"❌ Simulator error: {e}")

if __name__ == "__main__":
    # Install websockets if not available
    try:
        import websockets
    except ImportError:
        print("Installing websockets library...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "websockets"])
        import websockets
    
    asyncio.run(main())