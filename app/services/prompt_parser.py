import re
from dataclasses import dataclass, field

@dataclass
class ParsedPrompt:
    """Dataclass representing parsed and classified metadata from a prompt."""
    ui_type: str
    color_style: str
    sections: list[str] = field(default_factory=list)
    complexity_level: str = "simple"
    raw_prompt: str = ""

def parse(prompt: str) -> ParsedPrompt:
    """Parse, sanitize, and classify a user prompt for UI generation.
    
    Args:
        prompt: Raw prompt text from the user.
        
    Returns:
        ParsedPrompt object containing metadata classification.
    """
    if not prompt or not prompt.strip():
        return ParsedPrompt(
            ui_type="other",
            color_style="minimal",
            sections=[],
            complexity_level="simple",
            raw_prompt=""
        )

    # 1. Truncate long prompts to prevent downstream token overflow (limit to 2000 characters)
    max_len = 2000
    trimmed_prompt = prompt[:max_len]

    # 2. Sanitise prompt: remove HTML tags and block prompt injection patterns
    # Remove HTML-like tags
    sanitized = re.sub(r"<[^>]*?>", "", trimmed_prompt)

    # Clean up common prompt injection keywords/phrases
    injection_patterns = [
        r"(?i)ignore\s+all\s+previous\s+instructions",
        r"(?i)ignore\s+previous\s+instructions",
        r"(?i)forget\s+all\s+instructions",
        r"(?i)forget\s+(?:my|your)\s+instructions",
        r"(?i)forget\s+your\s+system\s+prompt",
        r"(?i)override\s+(?:your\s+)?guidelines",
        r"(?i)system\s+prompt\s+bypass",
        r"(?i)you\s+are\s+now\s+a\s+developer",
        r"(?i)do\s+not\s+output\s+react",
    ]
    for pattern in injection_patterns:
        sanitized = re.sub(pattern, "[removed]", sanitized)

    # 3. Normalize whitespace
    normalized = re.sub(r"\s+", " ", sanitized).strip()
    lowercase_normalized = normalized.lower()

    # 4. Classify UI Type
    ui_type = "other"
    ui_keywords = {
        "landing_page": ["landing page", "landing", "hero page", "marketing page", "home page"],
        "dashboard": ["dashboard", "analytics", "charts", "graphs", "stats", "admin panel", "tracking"],
        "form": ["form", "login", "signup", "register", "contact", "checkout", "payment"],
        "card": ["card", "profile card", "widget", "pricing card", "item card"],
        "navigation": ["navbar", "menu", "sidebar", "header", "footer", "navigation"]
    }
    
    # Check for direct keyword matches (highest priority to most specific term)
    for category, keywords in ui_keywords.items():
        if any(keyword in lowercase_normalized for keyword in keywords):
            ui_type = category
            break

    # 5. Classify Color Style
    color_style = "minimal"
    style_keywords = {
        "modern": ["modern", "neon", "vibrant", "dark mode", "gradient", "glassmorphism", "glowing"],
        "corporate": ["corporate", "business", "professional", "formal", "enterprise"],
        "playful": ["playful", "kids", "fun", "cartoon", "colorful", "pastel", "cute"],
        "minimal": ["minimal", "clean", "simple", "flat", "grayscale", "white", "black"]
    }
    
    for category, keywords in style_keywords.items():
        if any(keyword in lowercase_normalized for keyword in keywords):
            color_style = category
            break

    # 6. Extract Section Keywords
    section_mapping = {
        "hero": "hero",
        "pricing": "pricing",
        "features": "features",
        "feature": "features",
        "footer": "footer",
        "header": "header",
        "navbar": "navbar",
        "contact": "contact",
        "testimonials": "testimonials",
        "testimonial": "testimonials",
        "faq": "faq",
        "gallery": "gallery",
        "cta": "cta",
        "about": "about",
        "services": "services",
        "service": "services",
        "team": "team",
        "stats": "stats",
        "portfolio": "portfolio",
        "blog": "blog",
        "sidebar": "sidebar",
        "charts": "charts",
        "chart": "charts",
        "table": "table",
        "search": "search",
        "profile": "profile",
    }
    
    # We find keywords in prompt and keep their relative order in the list
    sections = []
    seen = set()
    for kw, sec_name in section_mapping.items():
        if kw in lowercase_normalized and sec_name not in seen:
            sections.append(sec_name)
            seen.add(sec_name)


    # 7. Classify Complexity
    section_count = len(sections)
    if section_count <= 1:
        complexity = "simple"
    elif section_count <= 3:
        complexity = "medium"
    else:
        complexity = "complex"

    return ParsedPrompt(
        ui_type=ui_type,
        color_style=color_style,
        sections=sections,
        complexity_level=complexity,
        raw_prompt=normalized
    )
