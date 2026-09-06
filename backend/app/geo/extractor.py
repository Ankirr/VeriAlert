"""
Location Extraction Module using spaCy NER (en_core_web_sm) + Regional Disaster Gazetteer.
Extracts, filters, and ranks geographical entities from disaster reports with
Title-Aware Hierarchical Extraction, Dateline Stripping, and Institutional Filtering.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Set
import spacy
from app.geo.gazetteer import REGIONAL_ALIASES, RIVER_BASIN_CONTEXT, STATE_CENTROIDS, resolve_alias

logger = logging.getLogger(__name__)

# Global cached spaCy model instance
_NLP_INSTANCE = None

def get_spacy_nlp():
    global _NLP_INSTANCE
    if _NLP_INSTANCE is None:
        logger.info("Loading spaCy NER model 'en_core_web_sm'...")
        _NLP_INSTANCE = spacy.load("en_core_web_sm")
    return _NLP_INSTANCE

# Non-geographical noise terms and institutional entities
EXCLUDED_ENTITIES: Set[str] = {
    "india", "world", "asian", "international", "reuters", "press", "associated press", "pti", "ani", "afp", "getty",
    "evening", "morning", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
    "police", "army", "navy", "air force", "iaf", "ndrf", "sdrf", "imd", "cwc", "bjp", "congress", "putin", "modi",
    "iit", "nit", "aiims", "iim", "iit kanpur", "iit delhi", "iit bombay", "iit roorkee", "iit madras", "iit kharagpur",
    "university", "college", "institute", "high court", "supreme court", "court", "station", "airport", "office", "centre"
}

# Regex to detect academic / institutional references
INSTITUTIONAL_PATTERN = re.compile(
    r'\b(iit|nit|aiims|iim|university|institute|college|court|police station|air force|hospital)\b',
    re.IGNORECASE
)

# Regex to match and strip news agency bureau datelines (e.g. "NEW DELHI: ", "KATHMANDU (Reuters) - ", "BEIJING -- ")
DATELINE_PATTERN = re.compile(
    r'^\s*(?:[A-Z\s]{2,20}(?:,\s*[A-Za-z\s]+)?|\([A-Za-z\s]+\))\s*[-–:]\s*',
    re.MULTILINE
)

class DisasterLocationExtractor:
    """
    Extracts geographical locations from raw text and titles using spaCy NER
    complemented by Indian disaster gazetteer and river-basin matching.
    """
    def __init__(self):
        self.nlp = get_spacy_nlp()

    def extract_locations(self, text: str, location_hint: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
        """
        Extracts and resolves locations from text and title.
        Prioritizes entities explicitly mentioned in the disaster title.
        """
        if not text and not title:
            return self._empty_result()

        # Step 1: Extract Title entities with highest priority
        title_candidates = []
        title_text_lower = (title or "").lower()
        if title:
            title_doc = self.nlp(title)
            for ent in title_doc.ents:
                if ent.label_ in ("GPE", "LOC", "FAC"):
                    cleaned = ent.text.strip().strip(",.!?\"'();:")
                    if self._is_valid_location_candidate(cleaned):
                        title_candidates.append(cleaned)
            
            # Match gazetteer aliases and states directly in title, skipping institutional mentions
            for alias_key in list(REGIONAL_ALIASES.keys()) + list(STATE_CENTROIDS.keys()):
                if re.search(r'\b(iit|nit|aiims|iim|university|institute|college)\s+' + re.escape(alias_key) + r'\b', title_text_lower):
                    continue
                pattern = r'\b' + re.escape(alias_key) + r'\b'
                if re.search(pattern, title_text_lower):
                    if alias_key not in ("india", "world") and not any(c.lower() == alias_key for c in title_candidates):
                        title_candidates.append(alias_key.title())

            for basin_name in RIVER_BASIN_CONTEXT.keys():
                if re.search(r'\b' + re.escape(basin_name) + r'\b', title_text_lower):
                    mb = basin_name.title()
                    if not any(c.lower() == basin_name for c in title_candidates):
                        title_candidates.append(mb)

        # Step 2: Clean body text (strip leading dateline) and extract body entities
        body_text = text or ""
        stripped_body = DATELINE_PATTERN.sub("", body_text)
        body_text_lower = stripped_body.lower()
        
        body_candidates = []
        body_doc = self.nlp(stripped_body[:800])
        for ent in body_doc.ents:
            if ent.label_ in ("GPE", "LOC", "FAC"):
                cleaned = ent.text.strip().strip(",.!?\"'();:")
                if self._is_valid_location_candidate(cleaned, body_text_lower):
                    body_candidates.append(cleaned)

        # Match gazetteer aliases and rivers in body
        for alias_key in list(REGIONAL_ALIASES.keys()) + list(STATE_CENTROIDS.keys()):
            if re.search(r'\b(iit|nit|aiims|iim|university|institute|college)\s+' + re.escape(alias_key) + r'\b', body_text_lower):
                continue
            pattern = r'\b' + re.escape(alias_key) + r'\b'
            if re.search(pattern, body_text_lower):
                if alias_key not in ("india", "world") and not any(c.lower() == alias_key for c in (title_candidates + body_candidates)):
                    body_candidates.append(alias_key.title())

        matched_basin = None
        for basin_name in RIVER_BASIN_CONTEXT.keys():
            pattern = r'\b' + re.escape(basin_name) + r'\b'
            if re.search(pattern, title_text_lower) or re.search(pattern, body_text_lower):
                matched_basin = basin_name.title()
                if not any(c.lower() == basin_name for c in (title_candidates + body_candidates)):
                    body_candidates.append(matched_basin)

        # Step 3: Integrate location hint if provided
        hint_candidates = []
        if location_hint and location_hint.strip():
            hint_clean = location_hint.strip().strip(",.!?\"'();:")
            if self._is_valid_location_candidate(hint_clean):
                hint_candidates.append(hint_clean)

        # Combine candidates with Title first, then Hint, then Body
        combined_candidates = title_candidates + hint_candidates + body_candidates
        if not combined_candidates:
            # Fallback to river basin if matched
            if matched_basin:
                combined_candidates = [matched_basin]
            else:
                return self._empty_result()

        # Step 4: Resolve and disambiguate candidates
        full_text_lower = f"{title_text_lower} {body_text_lower}"
        resolved_info = self._resolve_candidates(
            title_candidates=title_candidates,
            all_candidates=combined_candidates,
            title_text_lower=title_text_lower,
            full_text_lower=full_text_lower,
            matched_basin=matched_basin
        )
        return resolved_info

    def _is_valid_location_candidate(self, cand: str, context_text_lower: str = "") -> bool:
        """Validates that candidate is not institutional noise or excluded."""
        if len(cand) < 3:
            return False
        cl = cand.lower()
        if cl in EXCLUDED_ENTITIES:
            return False
        if INSTITUTIONAL_PATTERN.search(cl):
            return False
        if context_text_lower and re.search(r'\b(iit|nit|aiims|iim|university|institute|college)\s+' + re.escape(cl) + r'\b', context_text_lower):
            return False
        return True

    def _resolve_candidates(
        self,
        title_candidates: List[str],
        all_candidates: List[str],
        title_text_lower: str,
        full_text_lower: str,
        matched_basin: Optional[str]
    ) -> Dict[str, Any]:
        detected_city = None
        detected_state = None
        detected_country = None
        resolved_entity_name = None

        # --- Priority 1: Transboundary & Country Resolution ---
        # If title specifically mentions Tibet/China vs Nepal, respect title strictly
        if "tibet" in title_text_lower or "xizang" in title_text_lower:
            detected_country = "China"
            detected_state = "Tibet"
            detected_city = "Lhasa"
            resolved_entity_name = "Tibet"
        elif "nepal" in title_text_lower:
            detected_country = "Nepal"
            if "bhotekoshi" in full_text_lower:
                detected_city = "Bhotekoshi"
                detected_state = "Bagmati"
                resolved_entity_name = "Bhotekoshi"
            elif "melamchi" in full_text_lower:
                detected_city = "Melamchi"
                detected_state = "Bagmati"
                resolved_entity_name = "Melamchi"
            elif "sindhupalchok" in full_text_lower:
                detected_city = "Sindhupalchok"
                detected_state = "Bagmati"
                resolved_entity_name = "Sindhupalchok"
            elif "kathmandu" in title_text_lower:
                detected_city = "Kathmandu"
                detected_state = "Bagmati"
                resolved_entity_name = "Kathmandu"
            else:
                # Generic Nepal event
                resolved_entity_name = "Nepal"
        elif "china" in title_text_lower:
            detected_country = "China"
            resolved_entity_name = "China"

        # If not determined by title, check candidates
        if not detected_country:
            for cand in all_candidates:
                cl = cand.lower()
                if cl in ("xizang", "tibet", "lhasa"):
                    detected_country = "China"
                    detected_state = "Tibet"
                    detected_city = "Lhasa"
                    resolved_entity_name = "Xizang" if cl != "lhasa" else "Lhasa"
                    break
                elif cl in ("kathmandu", "bhotekoshi", "sindhupalchok", "pokhara", "darchula", "melamchi"):
                    detected_country = "Nepal"
                    detected_city = cl.title()
                    resolved_entity_name = cl.title()
                    break
                elif cl == "nepal":
                    detected_country = "Nepal"
                    resolved_entity_name = "Nepal"
                    break
                elif cl == "china":
                    detected_country = "China"
                    break

        # --- Priority 2: State & City Resolution from Title ---
        # First scan for state mentions in title (e.g. West Bengal, Odisha, Uttarakhand)
        for cand in title_candidates:
            cand_lower = cand.lower()
            if cand_lower in STATE_CENTROIDS and cand_lower not in ("india", "world", "china", "nepal"):
                detected_state = cand.title()
                if not resolved_entity_name:
                    resolved_entity_name = cand
                break

        # Then check specific gazetteer aliases in title
        for cand in title_candidates:
            cand_lower = cand.lower()
            alias = resolve_alias(cand_lower)
            if alias:
                if alias.get("state") and not detected_state:
                    detected_state = alias["state"]
                if alias.get("city") and not detected_city:
                    # Validate city against detected state
                    if not detected_state or alias.get("state", "").lower() == detected_state.lower():
                        detected_city = alias["city"]
                if alias.get("country") and not detected_country:
                    detected_country = alias["country"]
                if not resolved_entity_name:
                    resolved_entity_name = cand
                break

        # --- Priority 3: City & State Resolution from All Candidates ---
        # If no state from title, find state and city from candidates with strict cross-validation
        for cand in all_candidates:
            cand_lower = cand.lower()
            alias = resolve_alias(cand_lower)
            if alias:
                alias_state = alias.get("state")
                alias_city = alias.get("city")
                alias_country = alias.get("country")

                # If detected_state is already set, verify city belongs to that state!
                if detected_state:
                    if alias_state and alias_state.lower() == detected_state.lower():
                        if alias_city and not detected_city:
                            detected_city = alias_city
                            resolved_entity_name = cand
                else:
                    if alias_city and not detected_city:
                        detected_city = alias_city
                        resolved_entity_name = cand
                    if alias_state and not detected_state:
                        detected_state = alias_state
                    if alias_country and not detected_country:
                        detected_country = alias_country

        # Check for state mentions in remaining candidates if state not yet set
        if not detected_state:
            for cand in all_candidates:
                cand_lower = cand.lower()
                if cand_lower in STATE_CENTROIDS and cand_lower not in ("india", "world", "china", "nepal"):
                    detected_state = cand.title()
                    if not resolved_entity_name:
                        resolved_entity_name = cand
                    break

        # --- Priority 4: River Basin Mapping ---
        if matched_basin and not detected_state:
            basin_info = RIVER_BASIN_CONTEXT.get(matched_basin.lower())
            if basin_info:
                detected_state = basin_info.get("state", detected_state)
                detected_country = basin_info.get("country", detected_country)
                if not resolved_entity_name:
                    resolved_entity_name = f"{matched_basin} River Basin"

        # Default country
        if not detected_country:
            detected_country = "India"

        # Fallback entity name
        if not resolved_entity_name and all_candidates:
            resolved_entity_name = all_candidates[0]

        # Construct clean primary geocoding query
        query_parts = []
        if detected_city:
            query_parts.append(detected_city)
        elif resolved_entity_name and resolved_entity_name.lower() not in (detected_state or "").lower() and resolved_entity_name.lower() != (detected_country or "").lower():
            query_parts.append(resolved_entity_name)

        if detected_state and (not detected_city or detected_city.lower() != detected_state.lower()):
            if detected_state.lower() != (detected_country or "").lower():
                query_parts.append(detected_state)

        if detected_country:
            if not query_parts or detected_country.lower() != query_parts[-1].lower():
                query_parts.append(detected_country)

        primary_query = ", ".join(query_parts) if query_parts else (resolved_entity_name or detected_country or "India")

        # Fallback query
        fallback_parts = []
        if detected_state and detected_state.lower() != (detected_country or "").lower():
            fallback_parts.append(detected_state)
        if detected_country:
            fallback_parts.append(detected_country)
        fallback_query = ", ".join(fallback_parts) if fallback_parts else (detected_country or "India")

        return {
            "extracted_entities": list(dict.fromkeys(all_candidates)),
            "primary_location": primary_query,
            "fallback_location": fallback_query,
            "city": detected_city,
            "district": detected_city if detected_city else None,
            "state": detected_state,
            "country": detected_country,
            "is_regional": bool(detected_city or detected_state)
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "extracted_entities": [],
            "primary_location": "India",
            "fallback_location": "India",
            "city": None,
            "district": None,
            "state": None,
            "country": "India",
            "is_regional": False
        }
