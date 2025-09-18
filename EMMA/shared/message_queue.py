"""
EMMA Message Queue System
Handles Redis-based communication between system components
"""

import redis
import json
import logging
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timedelta
import asyncio
import uuid

from .data_models import EmmaAlert, SystemMetrics, UEStatus

logger = logging.getLogger(__name__)

class EmmaMessageQueue:
    """Redis-based message queue for EMMA system components"""
    
    # Channel names
    CHANNEL_ALERTS = "emma:alerts"
    CHANNEL_NETWORK_ALERTS = "emma:network_alerts"
    CHANNEL_UE_STATUS = "emma:ue_status"
    CHANNEL_SYSTEM_METRICS = "emma:metrics"
    
    # Storage keys
    KEY_ALERT_STORE = "emma:alert_store"
    KEY_UE_STORE = "emma:ue_store"
    KEY_METRICS_STORE = "emma:metrics_store"
    KEY_ACTIVE_UES = "emma:active_ues"
    
    def __init__(self, host='redis', port=6379, db=0):
        """Initialize Redis connection"""
        self.redis_client = redis.Redis(
            host=host, 
            port=port, 
            db=db, 
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True
        )
        self.pubsub = None
        self._test_connection()
    
    def _test_connection(self):
        """Test Redis connection"""
        try:
            self.redis_client.ping()
            logger.info("Successfully connected to Redis")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    # Alert Management
    def publish_alert(self, alert: EmmaAlert) -> bool:
        """Publish new alert to all subscribers"""
        try:
            alert_json = alert.to_json()
            
            # Store alert for retrieval
            self.store_alert(alert.identifier, alert)
            
            # Publish to alert channel
            result = self.redis_client.publish(self.CHANNEL_ALERTS, alert_json)
            logger.info(f"Published alert {alert.identifier} to {result} subscribers")
            return result > 0
        
        except Exception as e:
            logger.error(f"Failed to publish alert: {e}")
            return False
    
    def publish_network_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Publish alert for network distribution"""
        try:
            result = self.redis_client.publish(
                self.CHANNEL_NETWORK_ALERTS, 
                json.dumps(alert_data)
            )
            logger.info(f"Published network alert to {result} subscribers")
            return result > 0
        
        except Exception as e:
            logger.error(f"Failed to publish network alert: {e}")
            return False
    
    def store_alert(self, alert_id: str, alert: EmmaAlert) -> bool:
        """Store alert data for retrieval"""
        try:
            self.redis_client.hset(
                self.KEY_ALERT_STORE, 
                alert_id, 
                alert.to_json()
            )
            # Set expiration for the alert (24 hours)
            self.redis_client.expire(self.KEY_ALERT_STORE, 86400)
            return True
        
        except Exception as e:
            logger.error(f"Failed to store alert {alert_id}: {e}")
            return False
    
    def get_alert(self, alert_id: str) -> Optional[EmmaAlert]:
        """Retrieve stored alert"""
        try:
            data = self.redis_client.hget(self.KEY_ALERT_STORE, alert_id)
            if data:
                return EmmaAlert.from_json(data)
            return None
        
        except Exception as e:
            logger.error(f"Failed to retrieve alert {alert_id}: {e}")
            return None
    
    def get_all_alerts(self) -> List[EmmaAlert]:
        """Get all stored alerts"""
        try:
            alert_data = self.redis_client.hgetall(self.KEY_ALERT_STORE)
            alerts = []
            for alert_json in alert_data.values():
                alerts.append(EmmaAlert.from_json(alert_json))
            return alerts
        
        except Exception as e:
            logger.error(f"Failed to retrieve all alerts: {e}")
            return []
    
    # UE Management
    def register_ue(self, ue_status: UEStatus) -> bool:
        """Register a UE device"""
        try:
            ue_status.last_seen = datetime.now().isoformat()
            ue_status.connection_status = "connected"
            
            # Store UE data
            self.redis_client.hset(
                self.KEY_UE_STORE,
                ue_status.ue_id,
                json.dumps(ue_status.to_dict())
            )
            
            # Add to active UEs set
            self.redis_client.sadd(self.KEY_ACTIVE_UES, ue_status.ue_id)
            
            # Publish UE status update
            self.redis_client.publish(
                self.CHANNEL_UE_STATUS,
                json.dumps({
                    "action": "register",
                    "ue_id": ue_status.ue_id,
                    "data": ue_status.to_dict()
                })
            )
            
            logger.info(f"Registered UE {ue_status.ue_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to register UE {ue_status.ue_id}: {e}")
            return False
    
    def unregister_ue(self, ue_id: str) -> bool:
        """Unregister a UE device"""
        try:
            # Remove from active UEs
            self.redis_client.srem(self.KEY_ACTIVE_UES, ue_id)
            
            # Update connection status
            ue_data = self.redis_client.hget(self.KEY_UE_STORE, ue_id)
            if ue_data:
                ue_status = UEStatus.from_dict(json.loads(ue_data))
                ue_status.connection_status = "disconnected"
                ue_status.last_seen = datetime.now().isoformat()
                
                self.redis_client.hset(
                    self.KEY_UE_STORE,
                    ue_id,
                    json.dumps(ue_status.to_dict())
                )
            
            # Publish UE status update
            self.redis_client.publish(
                self.CHANNEL_UE_STATUS,
                json.dumps({
                    "action": "unregister",
                    "ue_id": ue_id
                })
            )
            
            logger.info(f"Unregistered UE {ue_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to unregister UE {ue_id}: {e}")
            return False
    
    def get_active_ues(self) -> List[str]:
        """Get list of active UE IDs"""
        try:
            return list(self.redis_client.smembers(self.KEY_ACTIVE_UES))
        except Exception as e:
            logger.error(f"Failed to get active UEs: {e}")
            return []
    
    def get_ue_status(self, ue_id: str) -> Optional[UEStatus]:
        """Get UE status information"""
        try:
            data = self.redis_client.hget(self.KEY_UE_STORE, ue_id)
            if data:
                return UEStatus.from_dict(json.loads(data))
            return None
        except Exception as e:
            logger.error(f"Failed to get UE status for {ue_id}: {e}")
            return None
    
    # Metrics Management
    def store_metrics(self, metrics: SystemMetrics) -> bool:
        """Store system metrics"""
        try:
            self.redis_client.hset(
                self.KEY_METRICS_STORE,
                metrics.timestamp,
                json.dumps(metrics.to_dict())
            )
            
            # Keep only last 24 hours of metrics
            cutoff = datetime.now() - timedelta(hours=24)
            cutoff_str = cutoff.isoformat()
            
            # Get all metric timestamps and remove old ones
            all_metrics = self.redis_client.hgetall(self.KEY_METRICS_STORE)
            for timestamp in all_metrics.keys():
                if timestamp < cutoff_str:
                    self.redis_client.hdel(self.KEY_METRICS_STORE, timestamp)
            
            # Publish metrics update
            self.redis_client.publish(
                self.CHANNEL_SYSTEM_METRICS,
                json.dumps(metrics.to_dict())
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")
            return False
    
    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        """Get the latest system metrics"""
        try:
            all_metrics = self.redis_client.hgetall(self.KEY_METRICS_STORE)
            if not all_metrics:
                return None
            
            # Get the most recent timestamp
            latest_timestamp = max(all_metrics.keys())
            metrics_data = json.loads(all_metrics[latest_timestamp])
            
            return SystemMetrics.from_dict(metrics_data)
        
        except Exception as e:
            logger.error(f"Failed to get latest metrics: {e}")
            return None
    
    # Subscription Management
    def subscribe_alerts(self) -> redis.client.PubSub:
        """Subscribe to alert notifications"""
        try:
            pubsub = self.redis_client.pubsub()
            pubsub.subscribe(self.CHANNEL_ALERTS)
            logger.info("Subscribed to alert channel")
            return pubsub
        except Exception as e:
            logger.error(f"Failed to subscribe to alerts: {e}")
            return None
    
    def subscribe_network_alerts(self) -> redis.client.PubSub:
        """Subscribe to network alert notifications"""
        try:
            pubsub = self.redis_client.pubsub()
            pubsub.subscribe(self.CHANNEL_NETWORK_ALERTS)
            logger.info("Subscribed to network alert channel")
            return pubsub
        except Exception as e:
            logger.error(f"Failed to subscribe to network alerts: {e}")
            return None
    
    def subscribe_ue_status(self) -> redis.client.PubSub:
        """Subscribe to UE status updates"""
        try:
            pubsub = self.redis_client.pubsub()
            pubsub.subscribe(self.CHANNEL_UE_STATUS)
            logger.info("Subscribed to UE status channel")
            return pubsub
        except Exception as e:
            logger.error(f"Failed to subscribe to UE status: {e}")
            return None
    
    def subscribe_metrics(self) -> redis.client.PubSub:
        """Subscribe to metrics updates"""
        try:
            pubsub = self.redis_client.pubsub()
            pubsub.subscribe(self.CHANNEL_SYSTEM_METRICS)
            logger.info("Subscribed to metrics channel")
            return pubsub
        except Exception as e:
            logger.error(f"Failed to subscribe to metrics: {e}")
            return None
    
    # Utility Methods
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on Redis connection"""
        try:
            # Test basic operations
            test_key = f"health_check_{uuid.uuid4().hex}"
            self.redis_client.set(test_key, "test", ex=10)
            value = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)
            
            info = self.redis_client.info()
            
            return {
                "status": "healthy" if value == "test" else "unhealthy",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "unknown"),
                "redis_version": info.get("redis_version", "unknown")
            }
        
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def cleanup(self):
        """Clean up connections"""
        try:
            if self.pubsub:
                self.pubsub.close()
            self.redis_client.close()
            logger.info("Cleaned up Redis connections")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Singleton instance for global use
_message_queue_instance = None

def get_message_queue(host='redis', port=6379, db=0) -> EmmaMessageQueue:
    """Get singleton message queue instance"""
    global _message_queue_instance
    if _message_queue_instance is None:
        _message_queue_instance = EmmaMessageQueue(host=host, port=port, db=db)
    return _message_queue_instance