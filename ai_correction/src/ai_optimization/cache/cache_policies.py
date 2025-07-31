"""
缓存策略（占位）
"""

class TTLCachePolicy:
    """TTL缓存策略"""
    
    def __init__(self, ttl=3600):
        self.ttl = ttl

class LRUCachePolicy:
    """LRU缓存策略"""
    
    def __init__(self, max_size=1000):
        self.max_size = max_size

class SizeLimitedCachePolicy:
    """大小限制缓存策略"""
    
    def __init__(self, max_size=100*1024*1024):
        self.max_size = max_size