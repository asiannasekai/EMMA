import asyncio
import json
import time
import websockets
import requests
import redis
import pytest
import logging
from datetime import datetime, timedelta
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmmaIntegrationTest:
    """
    End-to-end integration tests for the EMMA system
    Tests the complete pipeline from alert generation to UE delivery
    """
    
    def __init__(self):
        self.redis_client = None
        self.test_results = []
        
        # Service endpoints
        self.cap_generator_url = "http://cap-generator:8001"
        self.http_cdn_url = "http://http-cdn:3000" 
        self.alert_distributor_url = "http://alert-distributor:3001"
        self.websocket_url = "ws://alert-distributor:8080"
        self.redis_host = "redis"
        self.redis_port = 6379
        
    async def setup(self):
        """Initialize test environment"""
        logger.info("Setting up integration test environment...")
        
        # Connect to Redis
        self.redis_client = redis.Redis(
            host=self.redis_host, 
            port=self.redis_port, 
            decode_responses=True
        )
        
        # Wait for services to be ready
        await self._wait_for_services()
        
        # Clear any existing test data
        await self._cleanup_test_data()
        
        logger.info("Test environment setup complete")
    
    async def _wait_for_services(self, timeout=120):
        """Wait for all services to be healthy"""
        logger.info("Waiting for services to be ready...")
        
        services = [
            ("Redis", lambda: self.redis_client.ping()),
            ("HTTP CDN", lambda: requests.get(f"{self.http_cdn_url}/health").status_code == 200),
            ("Alert Distributor", lambda: requests.get(f"{self.alert_distributor_url}/health").status_code == 200)
        ]
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            all_ready = True
            for service_name, health_check in services:
                try:
                    if not health_check():
                        all_ready = False
                        break
                except Exception:
                    all_ready = False
                    break
            
            if all_ready:
                logger.info("All services are ready")
                return
            
            logger.info("Waiting for services...")
            await asyncio.sleep(5)
        
        raise TimeoutError("Services did not become ready within timeout")
    
    async def _cleanup_test_data(self):
        """Clean up any existing test data"""
        try:
            # Clear test keys from Redis
            test_keys = self.redis_client.keys("test:*")
            if test_keys:
                self.redis_client.delete(*test_keys)
            
            # Clear alert store
            self.redis_client.delete("emma:alert_store")
            self.redis_client.delete("emma:ue_store")
            self.redis_client.delete("emma:active_ues")
            
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    async def test_basic_alert_generation(self):
        """Test basic CAP alert generation"""
        logger.info("Testing basic alert generation...")
        
        test_alert = {
            'category': 'Safety',
            'event': 'Integration Test Alert',
            'urgency': 'Immediate',
            'severity': 'Extreme',
            'certainty': 'Observed',
            'description': 'This is an integration test alert',
            'headline': 'Test Emergency Alert'
        }
        
        try:
            # Generate alert via CAP generator
            response = requests.post(
                f"{self.cap_generator_url}/generate-alert",
                json=test_alert,
                timeout=30
            )
            
            assert response.status_code == 200, f"Alert generation failed: {response.status_code}"
            
            alert_data = response.json()
            assert 'identifier' in alert_data, "Alert missing identifier"
            
            self.test_results.append({
                'test': 'basic_alert_generation',
                'status': 'PASS',
                'alert_id': alert_data['identifier'],
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"✅ Basic alert generation test passed: {alert_data['identifier']}")
            return alert_data
            
        except Exception as e:
            self.test_results.append({
                'test': 'basic_alert_generation',
                'status': 'FAIL',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            logger.error(f"❌ Basic alert generation test failed: {e}")
            raise
    
    async def test_websocket_connection(self):
        """Test WebSocket connection to Alert Distributor"""
        logger.info("Testing WebSocket connection...")
        
        try:
            test_ue_id = f"test-ue-{uuid.uuid4().hex[:8]}"
            
            async with websockets.connect(self.websocket_url) as websocket:
                # Send registration message
                registration = {
                    'type': 'register',
                    'ueId': test_ue_id,
                    'location': {'lat': 37.7749, 'lon': -122.4194},
                    'capabilities': {
                        'supportsVideo': True,
                        'supportsImages': True,
                        'supportsAudio': True
                    }
                }
                
                await websocket.send(json.dumps(registration))
                
                # Wait for registration confirmation
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                message = json.loads(response)
                
                # Should receive welcome message first
                if message['type'] == 'welcome':
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    message = json.loads(response)
                
                assert message['type'] == 'registration_confirmed', f"Unexpected message type: {message['type']}"
                assert message['ueId'] == test_ue_id, "UE ID mismatch in confirmation"
                
                # Verify UE is registered in Redis
                await asyncio.sleep(1)  # Allow time for Redis update
                active_ues = self.redis_client.smembers('emma:active_ues')
                assert test_ue_id in active_ues, "UE not found in active UEs list"
                
                self.test_results.append({
                    'test': 'websocket_connection',
                    'status': 'PASS',
                    'ue_id': test_ue_id,
                    'timestamp': datetime.now().isoformat()
                })
                
                logger.info(f"✅ WebSocket connection test passed: {test_ue_id}")
                return test_ue_id
                
        except Exception as e:
            self.test_results.append({
                'test': 'websocket_connection',
                'status': 'FAIL',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            logger.error(f"❌ WebSocket connection test failed: {e}")
            raise
    
    async def test_end_to_end_alert_delivery(self):
        """Test complete alert delivery pipeline"""
        logger.info("Testing end-to-end alert delivery...")
        
        try:
            # Step 1: Connect UE via WebSocket
            test_ue_id = f"test-ue-{uuid.uuid4().hex[:8]}"
            alert_received = asyncio.Event()
            received_alert = None
            
            async def ue_connection():
                nonlocal received_alert
                
                async with websockets.connect(self.websocket_url) as websocket:
                    # Register UE
                    registration = {
                        'type': 'register',
                        'ueId': test_ue_id,
                        'location': {'lat': 37.7749, 'lon': -122.4194}
                    }
                    await websocket.send(json.dumps(registration))
                    
                    # Wait for registration confirmation
                    while True:
                        response = await websocket.recv()
                        message = json.loads(response)
                        
                        if message['type'] == 'registration_confirmed':
                            logger.info(f"UE {test_ue_id} registered successfully")
                            break
                        elif message['type'] == 'emergency_alert':
                            received_alert = message
                            alert_received.set()
                            logger.info(f"UE {test_ue_id} received emergency alert")
                            
                            # Send acknowledgment
                            ack = {
                                'type': 'alert_ack',
                                'alertId': message['alert']['identifier'],
                                'received': True,
                                'displayed': True
                            }
                            await websocket.send(json.dumps(ack))
                            break
            
            # Start UE connection in background
            ue_task = asyncio.create_task(ue_connection())
            
            # Wait a moment for UE to register
            await asyncio.sleep(2)
            
            # Step 2: Generate and publish alert
            test_alert = {
                'category': 'Safety',
                'event': 'End-to-End Test Alert',
                'urgency': 'Immediate',
                'severity': 'Extreme',
                'certainty': 'Observed',
                'description': 'This is an end-to-end integration test alert',
                'headline': 'E2E Test Emergency'
            }
            
            # Publish alert directly to Redis (simulating CAP generator)
            alert_id = f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
            test_alert['identifier'] = alert_id
            test_alert['sender'] = 'integration-test'
            test_alert['sent'] = datetime.now().isoformat()
            test_alert['status'] = 'Actual'
            test_alert['msgType'] = 'Alert'
            test_alert['scope'] = 'Public'
            
            # Publish to Redis
            self.redis_client.publish('emma:alerts', json.dumps(test_alert))
            
            # Step 3: Wait for alert delivery
            try:
                await asyncio.wait_for(alert_received.wait(), timeout=30)
                await ue_task
                
                # Verify alert was received correctly
                assert received_alert is not None, "No alert received by UE"
                assert received_alert['type'] == 'emergency_alert', "Wrong message type received"
                assert received_alert['alert']['identifier'] == alert_id, "Alert ID mismatch"
                assert received_alert['alert']['description'] == test_alert['description'], "Alert content mismatch"
                
                self.test_results.append({
                    'test': 'end_to_end_alert_delivery',
                    'status': 'PASS',
                    'alert_id': alert_id,
                    'ue_id': test_ue_id,
                    'delivery_time': (datetime.now() - datetime.fromisoformat(test_alert['sent'].replace('Z', '+00:00').replace('+00:00', ''))).total_seconds(),
                    'timestamp': datetime.now().isoformat()
                })
                
                logger.info(f"✅ End-to-end alert delivery test passed: {alert_id} → {test_ue_id}")
                
            except asyncio.TimeoutError:
                ue_task.cancel()
                raise TimeoutError("Alert not received within timeout period")
                
        except Exception as e:
            self.test_results.append({
                'test': 'end_to_end_alert_delivery',
                'status': 'FAIL',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            logger.error(f"❌ End-to-end alert delivery test failed: {e}")
            raise
    
    async def test_multiple_ue_delivery(self):
        """Test alert delivery to multiple UEs simultaneously"""
        logger.info("Testing multiple UE alert delivery...")
        
        try:
            num_ues = 5
            ue_tasks = []
            alert_received_events = []
            received_alerts = {}
            
            async def create_ue_connection(ue_index):
                ue_id = f"test-ue-multi-{ue_index}-{uuid.uuid4().hex[:8]}"
                alert_received = asyncio.Event()
                alert_received_events.append(alert_received)
                
                async with websockets.connect(self.websocket_url) as websocket:
                    # Register UE
                    registration = {
                        'type': 'register',
                        'ueId': ue_id,
                        'location': {'lat': 37.7749 + ue_index * 0.001, 'lon': -122.4194 + ue_index * 0.001}
                    }
                    await websocket.send(json.dumps(registration))
                    
                    # Wait for messages
                    while True:
                        response = await websocket.recv()
                        message = json.loads(response)
                        
                        if message['type'] == 'registration_confirmed':
                            logger.info(f"UE {ue_id} registered")
                            continue
                        elif message['type'] == 'emergency_alert':
                            received_alerts[ue_id] = message
                            alert_received.set()
                            logger.info(f"UE {ue_id} received alert")
                            
                            # Send acknowledgment
                            ack = {
                                'type': 'alert_ack',
                                'alertId': message['alert']['identifier'],
                                'received': True,
                                'displayed': True
                            }
                            await websocket.send(json.dumps(ack))
                            break
            
            # Create multiple UE connections
            for i in range(num_ues):
                task = asyncio.create_task(create_ue_connection(i))
                ue_tasks.append(task)
            
            # Wait for all UEs to register
            await asyncio.sleep(3)
            
            # Generate and publish alert
            alert_id = f"MULTI-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
            test_alert = {
                'identifier': alert_id,
                'sender': 'multi-ue-test',
                'sent': datetime.now().isoformat(),
                'status': 'Actual',
                'msgType': 'Alert',
                'scope': 'Public',
                'category': 'Safety',
                'event': 'Multi-UE Test Alert',
                'urgency': 'Immediate',
                'severity': 'Extreme',
                'certainty': 'Observed',
                'description': 'This is a multi-UE integration test alert',
                'headline': 'Multi-UE Test Emergency'
            }
            
            # Publish alert
            self.redis_client.publish('emma:alerts', json.dumps(test_alert))
            
            # Wait for all UEs to receive the alert
            try:
                await asyncio.wait_for(
                    asyncio.gather(*[event.wait() for event in alert_received_events]),
                    timeout=30
                )
                
                # Wait for all tasks to complete
                await asyncio.gather(*ue_tasks)
                
                # Verify all UEs received the alert
                assert len(received_alerts) == num_ues, f"Expected {num_ues} UEs to receive alert, got {len(received_alerts)}"
                
                for ue_id, alert_message in received_alerts.items():
                    assert alert_message['alert']['identifier'] == alert_id, f"Alert ID mismatch for UE {ue_id}"
                
                self.test_results.append({
                    'test': 'multiple_ue_delivery',
                    'status': 'PASS',
                    'alert_id': alert_id,
                    'num_ues': num_ues,
                    'successful_deliveries': len(received_alerts),
                    'timestamp': datetime.now().isoformat()
                })
                
                logger.info(f"✅ Multiple UE delivery test passed: {alert_id} delivered to {len(received_alerts)} UEs")
                
            except asyncio.TimeoutError:
                # Cancel any pending tasks
                for task in ue_tasks:
                    if not task.done():
                        task.cancel()
                
                raise TimeoutError(f"Not all UEs received alert within timeout. Received by {len(received_alerts)}/{num_ues} UEs")
                
        except Exception as e:
            self.test_results.append({
                'test': 'multiple_ue_delivery',
                'status': 'FAIL',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            logger.error(f"❌ Multiple UE delivery test failed: {e}")
            raise
    
    async def test_system_performance(self):
        """Test system performance under load"""
        logger.info("Testing system performance...")
        
        try:
            # Generate multiple alerts rapidly
            num_alerts = 10
            alerts_generated = []
            
            for i in range(num_alerts):
                alert_id = f"PERF-TEST-{i}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                test_alert = {
                    'identifier': alert_id,
                    'sender': 'performance-test',
                    'sent': datetime.now().isoformat(),
                    'status': 'Actual',
                    'msgType': 'Alert',
                    'scope': 'Public',
                    'category': 'Safety',
                    'event': f'Performance Test Alert {i+1}',
                    'urgency': 'Immediate',
                    'severity': 'Moderate',
                    'certainty': 'Observed',
                    'description': f'Performance test alert number {i+1}',
                    'headline': f'Perf Test {i+1}'
                }
                
                alerts_generated.append(test_alert)
                self.redis_client.publish('emma:alerts', json.dumps(test_alert))
                
                # Small delay between alerts
                await asyncio.sleep(0.1)
            
            # Check system metrics
            await asyncio.sleep(5)  # Allow time for processing
            
            # Verify Redis is still responsive
            redis_start = time.time()
            self.redis_client.ping()
            redis_response_time = time.time() - redis_start
            
            # Check Alert Distributor health
            distributor_start = time.time()
            health_response = requests.get(f"{self.alert_distributor_url}/health", timeout=10)
            distributor_response_time = time.time() - distributor_start
            
            assert health_response.status_code == 200, "Alert Distributor health check failed"
            assert redis_response_time < 1.0, f"Redis response time too slow: {redis_response_time}s"
            assert distributor_response_time < 2.0, f"Distributor response time too slow: {distributor_response_time}s"
            
            self.test_results.append({
                'test': 'system_performance',
                'status': 'PASS',
                'alerts_generated': num_alerts,
                'redis_response_time': redis_response_time,
                'distributor_response_time': distributor_response_time,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"✅ System performance test passed: {num_alerts} alerts, Redis: {redis_response_time:.3f}s, Distributor: {distributor_response_time:.3f}s")
            
        except Exception as e:
            self.test_results.append({
                'test': 'system_performance',
                'status': 'FAIL',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            logger.error(f"❌ System performance test failed: {e}")
            raise
    
    async def run_all_tests(self):
        """Run all integration tests"""
        logger.info("🚀 Starting EMMA Integration Tests")
        
        try:
            await self.setup()
            
            # Run individual tests
            test_methods = [
                self.test_basic_alert_generation,
                self.test_websocket_connection,
                self.test_end_to_end_alert_delivery,
                self.test_multiple_ue_delivery,
                self.test_system_performance
            ]
            
            for test_method in test_methods:
                try:
                    await test_method()
                except Exception as e:
                    logger.error(f"Test {test_method.__name__} failed: {e}")
                    # Continue with other tests
                
                # Brief pause between tests
                await asyncio.sleep(2)
            
            # Generate test report
            await self._generate_test_report()
            
        except Exception as e:
            logger.error(f"Integration test setup failed: {e}")
            raise
        finally:
            await self._cleanup_test_data()
    
    async def _generate_test_report(self):
        """Generate and save test report"""
        report = {
            'test_run_id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.test_results),
            'passed_tests': len([r for r in self.test_results if r['status'] == 'PASS']),
            'failed_tests': len([r for r in self.test_results if r['status'] == 'FAIL']),
            'test_results': self.test_results
        }
        
        # Save to Redis
        self.redis_client.set(
            f"emma:test_report:{report['test_run_id']}", 
            json.dumps(report, indent=2),
            ex=86400  # Expire after 24 hours
        )
        
        # Log summary
        logger.info("=" * 60)
        logger.info("EMMA INTEGRATION TEST REPORT")
        logger.info("=" * 60)
        logger.info(f"Test Run ID: {report['test_run_id']}")
        logger.info(f"Total Tests: {report['total_tests']}")
        logger.info(f"Passed: {report['passed_tests']}")
        logger.info(f"Failed: {report['failed_tests']}")
        logger.info(f"Success Rate: {(report['passed_tests']/report['total_tests']*100):.1f}%")
        logger.info("=" * 60)
        
        for result in self.test_results:
            status_emoji = "✅" if result['status'] == 'PASS' else "❌"
            logger.info(f"{status_emoji} {result['test']}: {result['status']}")
            if result['status'] == 'FAIL':
                logger.info(f"   Error: {result.get('error', 'Unknown error')}")
        
        logger.info("=" * 60)

# Test execution
async def main():
    """Main test execution function"""
    test_runner = EmmaIntegrationTest()
    await test_runner.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())