import logging
import asyncio
from abc import ABC, abstractmethod
from typing import List
from app.models.schemas import NormalizedDisasterItem

logger = logging.getLogger(__name__)

class BaseCollector(ABC):
    def __init__(self, source_name: str, source_type: str):
        self.source_name = source_name
        self.source_type = source_type

    @abstractmethod
    async def fetch(self) -> List[NormalizedDisasterItem]:
        """Fetch raw items and return normalized disaster items."""
        pass

    async def fetch_with_retry(self, max_retries: int = 3, initial_delay: float = 1.0) -> List[NormalizedDisasterItem]:
        """Executes fetch with exponential backoff for compliance and rate-limiting resilience."""
        delay = initial_delay
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[{self.source_name}] Attempt {attempt} fetching data...")
                return await self.fetch()
            except Exception as e:
                logger.warning(f"[{self.source_name}] Attempt {attempt} failed: {e}")
                if attempt == max_retries:
                    logger.error(f"[{self.source_name}] All {max_retries} retries failed.")
                    return []
                await asyncio.sleep(delay)
                delay *= 2
        return []
