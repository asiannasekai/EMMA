import pytest
import asyncio
import logging
from integration_test import EmmaIntegrationTest

# Configure pytest logging
logging.basicConfig(level=logging.INFO)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_runner():
    """Create and setup test runner for the session."""
    runner = EmmaIntegrationTest()
    await runner.setup()
    yield runner
    await runner._cleanup_test_data()

@pytest.mark.asyncio
async def test_basic_alert_generation(test_runner):
    """Test basic CAP alert generation."""
    await test_runner.test_basic_alert_generation()

@pytest.mark.asyncio
async def test_websocket_connection(test_runner):
    """Test WebSocket connection to Alert Distributor."""
    await test_runner.test_websocket_connection()

@pytest.mark.asyncio
async def test_end_to_end_alert_delivery(test_runner):
    """Test complete alert delivery pipeline."""
    await test_runner.test_end_to_end_alert_delivery()

@pytest.mark.asyncio
async def test_multiple_ue_delivery(test_runner):
    """Test alert delivery to multiple UEs simultaneously."""
    await test_runner.test_multiple_ue_delivery()

@pytest.mark.asyncio
async def test_system_performance(test_runner):
    """Test system performance under load."""
    await test_runner.test_system_performance()

@pytest.mark.asyncio
async def test_full_integration(test_runner):
    """Run all tests in sequence."""
    await test_runner.run_all_tests()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])