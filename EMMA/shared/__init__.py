"""
EMMA Shared Module
Common utilities and interfaces for EMMA system components
"""

from .data_models import (
    EmmaAlert,
    MediaAttachment,
    AlertArea,
    SystemMetrics,
    UEStatus,
    AlertSeverity,
    AlertUrgency,
    AlertCertainty
)

from .message_queue import EmmaMessageQueue, get_message_queue

__all__ = [
    'EmmaAlert',
    'MediaAttachment', 
    'AlertArea',
    'SystemMetrics',
    'UEStatus',
    'AlertSeverity',
    'AlertUrgency', 
    'AlertCertainty',
    'EmmaMessageQueue',
    'get_message_queue'
]