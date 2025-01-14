from pycountry import languages
from typing import Optional

def get_language_name(iso_code: str) -> Optional[str]:
    """
    Convert ISO 639-3 language code to its full name.
    Returns None if the code is not found.
    
    Example:
        get_language_name('cmn') -> 'Mandarin Chinese'
        get_language_name('spa') -> 'Spanish'
    """
    try:
        return languages.get(alpha_3=iso_code).name
    except AttributeError:
        return None

# Add custom mappings for languages that might not be in pycountry
CUSTOM_LANGUAGE_NAMES = {   
    'klg': 'Klingon',    # Star Trek - Has official dictionary, institute, and many speakers
    'qya': 'Quenya',     # Tolkien's High Elvish - Extensively documented by Tolkien himself
    'sjn': 'Sindarin',   # Tolkien's Elvish - Well documented with substantial vocabulary
    'dth': 'Dothraki',   # Game of Thrones - Created by linguist David Peterson, has official dictionary
    'hva': 'High Valyrian' # Game of Thrones - Created by Peterson, has Duolingo course and extensive documentation
}

def get_language_name_with_fallback(iso_code: str) -> str:
    """
    Get language name with fallback to custom mappings.
    Returns the ISO code itself if no name is found.
    """
    if iso_code in CUSTOM_LANGUAGE_NAMES:
        return CUSTOM_LANGUAGE_NAMES[iso_code]
    
    name = get_language_name(iso_code)
    return name if name else iso_code 