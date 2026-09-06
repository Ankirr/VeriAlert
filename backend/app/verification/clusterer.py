"""
Semantic Incident Clustering Module.
Groups related disaster reports into distinct incident clusters using
SentenceTransformers embeddings, spatial distance, and disaster type matching.
"""
import math
import uuid
import logging
from typing import List, Dict, Any, Tuple
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Global cached embedding model
_EMBEDDER_INSTANCE = None

def get_embedder():
    global _EMBEDDER_INSTANCE
    if _EMBEDDER_INSTANCE is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading SentenceTransformer 'all-MiniLM-L6-v2' on {device}...")
        _EMBEDDER_INSTANCE = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    return _EMBEDDER_INSTANCE

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance in kilometers between two GPS points."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class DisasterEventClusterer:
    """
    Clusters disaster reports into cohesive real-world incident clusters
    combining semantic embeddings, disaster type, and geospatial proximity.
    """
    def __init__(self, sim_threshold: float = 0.48, max_geo_dist_km: float = 75.0):
        self.embedder = get_embedder()
        self.sim_threshold = sim_threshold
        self.max_geo_dist_km = max_geo_dist_km

    def cluster_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes a list of enriched disaster item dicts and groups them into clusters.
        Each item dict should have: {id, title, raw_text, disaster_type, location_text, latitude, longitude, source, etc.}
        """
        if not items:
            return []

        logger.info(f"Clustering {len(items)} relevant disaster items...")

        # Prepare texts for embedding
        texts = [f"{item.get('title') or ''}. {item.get('raw_text', '')[:250]}" for item in items]
        embeddings = self.embedder.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        
        # Pairwise cosine similarity matrix
        sim_matrix = np.dot(embeddings, embeddings.T)

        n = len(items)
        adj_matrix = np.zeros((n, n), dtype=bool)

        for i in range(n):
            adj_matrix[i, i] = True
            for j in range(i + 1, n):
                item_a = items[i]
                item_b = items[j]

                # Check 1: Disaster type compatibility
                type_a = item_a.get("disaster_type", "general_disaster")
                type_b = item_b.get("disaster_type", "general_disaster")
                type_match = (type_a == type_b) or ("general" in type_a or "general" in type_b)

                if not type_match:
                    continue

                # Check 2: Strict Geospatial proximity (Events MUST be within 75km)
                lat_a, lon_a = item_a.get("latitude"), item_a.get("longitude")
                lat_b, lon_b = item_b.get("latitude"), item_b.get("longitude")
                loc_a = (item_a.get("location_text") or "").strip().lower()
                loc_b = (item_b.get("location_text") or "").strip().lower()

                geo_compatible = False
                if lat_a is not None and lon_a is not None and lat_b is not None and lon_b is not None:
                    dist_km = haversine_distance_km(lat_a, lon_a, lat_b, lon_b)
                    # Strictly enforce maximum distance threshold: disasters > 75km apart are distinct events
                    if dist_km <= self.max_geo_dist_km:
                        geo_compatible = True
                    else:
                        geo_compatible = False
                elif loc_a and loc_b and loc_a == loc_b:
                    # If coordinates missing but exact same city/district
                    geo_compatible = True

                # If not spatially compatible, they CANNOT be the same incident cluster
                if not geo_compatible:
                    continue

                # Check 3: Semantic similarity within local area
                sim = float(sim_matrix[i, j])
                if sim >= self.sim_threshold:
                    adj_matrix[i, j] = True
                    adj_matrix[j, i] = True

        # Connected components to form clusters
        visited = set()
        raw_clusters = []

        for i in range(n):
            if i not in visited:
                component = []
                queue = [i]
                visited.add(i)
                while queue:
                    curr = queue.pop(0)
                    component.append(curr)
                    for neighbor in range(n):
                        if adj_matrix[curr, neighbor] and neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                raw_clusters.append(component)

        # Build structured cluster dictionaries
        structured_clusters = []
        for component_indices in raw_clusters:
            cluster_items_list = [items[idx] for idx in component_indices]
            cluster_dict = self._build_cluster_summary(cluster_items_list)
            structured_clusters.append(cluster_dict)

        # Sort clusters by member count descending (largest events first)
        structured_clusters.sort(key=lambda c: len(c["items"]), reverse=True)
        logger.info(f"Formed {len(structured_clusters)} distinct event clusters from {len(items)} items.")
        return structured_clusters

    def _build_cluster_summary(self, cluster_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        cluster_id = str(uuid.uuid4())
        
        # Determine dominant disaster type
        type_counts = {}
        for it in cluster_items:
            t = it.get("disaster_type") or "general_disaster"
            type_counts[t] = type_counts.get(t, 0) + 1
        dominant_type = max(type_counts, key=type_counts.get)

        # Centroid coordinates
        # Pick the most informative title and anchor report
        sorted_by_informativeness = sorted(
            cluster_items,
            key=lambda x: (
                1 if not x.get("is_mock", False) else 0,
                1 if x.get("latitude") is not None else 0,
                len(x.get("title") or "")
            ),
            reverse=True
        )
        anchor_item = sorted_by_informativeness[0]

        # Location name and coordinates from anchor item (fallback to centroid if needed)
        dominant_loc = anchor_item.get("location_text")
        if not dominant_loc:
            loc_counts = {}
            for it in cluster_items:
                loc = it.get("location_text")
                if loc:
                    loc_counts[loc] = loc_counts.get(loc, 0) + 1
            dominant_loc = max(loc_counts, key=loc_counts.get) if loc_counts else "India"

        if anchor_item.get("latitude") is not None and anchor_item.get("longitude") is not None:
            centroid_lat = anchor_item["latitude"]
            centroid_lon = anchor_item["longitude"]
        else:
            valid_lats = [it["latitude"] for it in cluster_items if it.get("latitude") is not None]
            valid_lons = [it["longitude"] for it in cluster_items if it.get("longitude") is not None]
            centroid_lat = round(float(np.mean(valid_lats)), 6) if valid_lats else 20.5937
            centroid_lon = round(float(np.mean(valid_lons)), 6) if valid_lons else 78.9629

        # Independent sources
        sources = list(dict.fromkeys(it.get("source", "Unknown") for it in cluster_items))

        canonical_title = anchor_item.get("title") or f"{dominant_type.title()} Alert in {dominant_loc}"

        return {
            "cluster_id": cluster_id,
            "event_name": canonical_title,
            "disaster_type": dominant_type,
            "location_name": dominant_loc,
            "latitude": centroid_lat,
            "longitude": centroid_lon,
            "items": cluster_items,
            "item_ids": [it["id"] for it in cluster_items],
            "sources": sources,
            "item_count": len(cluster_items),
            "independent_sources_count": len(sources)
        }
