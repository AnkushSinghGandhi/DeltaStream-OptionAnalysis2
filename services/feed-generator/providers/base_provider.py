from abc import ABC, abstractmethod


class BaseFeedProvider(ABC):
    """Abstract base class for all feed providers"""
    
    @abstractmethod
    def connect(self):
        """Establish connection to data source"""
        pass
    
    @abstractmethod
    def run(self):
        """Main loop - fetch and publish data"""
        pass
    
    @abstractmethod
    def publish_to_redis(self, channel: str, data: dict):
        """Publish data to Redis"""
        pass
