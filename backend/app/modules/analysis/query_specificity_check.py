"""Quick validation that analysis addresses the query."""

from __future__ import annotations

import logging

logger = logging.getLogger("mil_evid")


class QuerySpecificityChecker:
    """Validate that analysis is query-specific, not generic."""
    
    COUNTRIES = {
        'india', 'pakistan', 'ukraine', 'russia', 'china', 'usa',
        'iran', 'israel', 'palestine', 'france', 'uk', 'afghanistan',
        'germany' ,'colombia'
    }
    
    PRINCIPLE_WORDS = {
        'principle', 'obligation', 'obliged', 'requirement', 'must', 'shall',
        'customary', 'establishes', 'requires'
    }
    
    INCIDENT_WORDS = {
        'attack', 'incident', 'event', 'bombing', 'strike', 'reported',
        'casualties', 'fatalities', 'deaths', 'killed', 'injured',
        'damaged', 'destroyed', 'occurred'
    }
    
    @classmethod
    def check_military_analysis(
        cls,
        *,
        query: str,
        analysis: str,
    ) -> tuple[bool, str]:
        """Check if military analysis is query-specific."""
        
        # Extract query entities
        query_lower = query.lower()
        query_countries = [c for c in cls.COUNTRIES if c in query_lower]
        
        if not query_countries:
            # Not a country-specific query
            return True, "Not country-specific"
        
        analysis_lower = analysis.lower()
        
        # Check: Countries mentioned in analysis
        analysis_countries = [c for c in query_countries if c in analysis_lower]
        
        if not analysis_countries:
            msg = f"Query mentions {query_countries} but analysis doesn't"
            logger.warning(msg)
            return False, msg
        
        # Check: Incident content (not just principles)
        principle_count = sum(
            1 for w in cls.PRINCIPLE_WORDS
            if f" {w} " in f" {analysis_lower} "
        )
        
        incident_count = sum(
            1 for w in cls.INCIDENT_WORDS
            if f" {w} " in f" {analysis_lower} "
        )
        
        # If too many principles and too few incidents = generic
        if principle_count > 6 and incident_count < 2:
            msg = f"Too generic: {principle_count} principles vs {incident_count} incidents"
            logger.warning(msg)
            return False, msg
        
        return True, "Query-specific"

    @classmethod
    def check_analysis(
        cls,
        *,
        query: str,
        analysis: str,
    ) -> tuple[bool, str]:
        """Check whether analysis is specific to the supplied query."""
        return cls.check_military_analysis(
            query=query,
            analysis=analysis,
        )