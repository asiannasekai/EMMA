"""
EMMA Shared Data Models
Defines common data structures for inter-component communication
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from enum import Enum

class AlertSeverity(Enum):
    MINOR = "Minor"
    MODERATE = "Moderate"
    SEVERE = "Severe"
    EXTREME = "Extreme"

class AlertUrgency(Enum):
    IMMEDIATE = "Immediate"
    EXPECTED = "Expected"
    FUTURE = "Future"
    PAST = "Past"

class AlertCertainty(Enum):
    OBSERVED = "Observed"
    LIKELY = "Likely"
    POSSIBLE = "Possible"
    UNLIKELY = "Unlikely"

@dataclass
class MediaAttachment:
    """Represents a media attachment in an emergency alert"""
    filename: str
    content_type: str
    size: int
    checksum: str
    signature: Optional[str] = None
    url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MediaAttachment':
        return cls(**data)

@dataclass
class AlertArea:
    """Represents the geographical area affected by an alert"""
    area_desc: str
    polygon: Optional[str] = None
    circle: Optional[str] = None
    geocode: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertArea':
        return cls(**data)

@dataclass
class EmmaAlert:
    """Main alert data structure for EMMA system"""
    # CAP Required fields
    identifier: str
    sender: str
    sent: str
    status: str
    msg_type: str
    scope: str
    
    # Info block
    category: str
    event: str
    urgency: str
    severity: str
    certainty: str
    headline: str
    description: str
    instruction: Optional[str] = None
    web: Optional[str] = None
    contact: Optional[str] = None
    
    # Areas and media
    areas: List[AlertArea] = None
    media_attachments: List[MediaAttachment] = None
    
    # System metadata
    created_at: Optional[str] = None
    processed_at: Optional[str] = None
    expires_at: Optional[str] = None
    
    def __post_init__(self):
        if self.areas is None:
            self.areas = []
        if self.media_attachments is None:
            self.media_attachments = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_json(self) -> str:
        """Convert alert to JSON string"""
        return json.dumps(self.to_dict(), default=str, indent=2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'EmmaAlert':
        """Create alert from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmmaAlert':
        """Create alert from dictionary"""
        # Convert nested objects
        if 'areas' in data and data['areas']:
            data['areas'] = [AlertArea.from_dict(area) for area in data['areas']]
        
        if 'media_attachments' in data and data['media_attachments']:
            data['media_attachments'] = [MediaAttachment.from_dict(media) for media in data['media_attachments']]
        
        return cls(**data)
    
    def has_media(self) -> bool:
        """Check if alert has media attachments"""
        return bool(self.media_attachments)
    
    def is_high_priority(self) -> bool:
        """Check if alert is high priority based on severity and urgency"""
        return (self.severity in [AlertSeverity.SEVERE.value, AlertSeverity.EXTREME.value] 
                and self.urgency == AlertUrgency.IMMEDIATE.value)

@dataclass
class SystemMetrics:
    """System performance and status metrics"""
    timestamp: str
    total_alerts_generated: int
    total_alerts_distributed: int
    active_ue_connections: int
    average_delivery_time: float
    system_status: str
    component_status: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemMetrics':
        return cls(**data)

@dataclass
class UEStatus:
    """User Equipment status information"""
    ue_id: str
    location: Optional[Dict[str, float]] = None
    connection_status: str = "disconnected"
    last_seen: Optional[str] = None
    alerts_received: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UEStatus':
        return cls(**data)