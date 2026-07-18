"""Meta-memory checklists and gap detection."""

from __future__ import annotations

import logging
from app.memory.models import Memory

logger = logging.getLogger(__name__)

# Topic checklists per persona
DOMAINS = {
    "volta": {
        "budget range": ["bill", "zar", "rand", "cost", "price", "budget", "afford"],
        "property type": ["bedroom", "home", "house", "apartment", "flat", "townhouse", "roof", "property"],
        "backup requirement": ["backup", "load-shedding", "loadshedding", "outage", "battery", "stage"],
        "timeline urgency": ["timeline", "soon", "month", "week", "year", "install", "urgency"],
        "financing interest": ["finance", "loan", "rent-to-own", "lease", "upfront", "financing"]
    },
    "study_coach": {
        "study subject": ["subject", "math", "science", "biology", "history", "english", "physics", "chemistry"],
        "current grade": ["grade", "mark", "score", "percent", "%", "average"],
        "learning goal": ["goal", "pass", "excel", "improve", "understand", "aim"],
        "weekly study hours": ["hour", "time", "week", "schedule", "study hours"],
        "exam date": ["exam", "test", "date", "schedule", "deadline", "june", "november", "tomorrow"]
    }
}


def find_missing_topics(memories: list[Memory], persona: str = "volta") -> list[str]:
    """Identify which expected topics have no corresponding active memories."""
    checklist = DOMAINS.get(persona.lower(), DOMAINS["volta"])
    
    active_observations = [m.observation.lower() for m in memories if not m.is_superseded]
    
    missing = []
    for topic, keywords in checklist.items():
        found = False
        for obs in active_observations:
            for kw in keywords:
                if kw in obs:
                    found = True
                    break
            if found:
                break
        if not found:
            missing.append(topic)
            
    return missing
