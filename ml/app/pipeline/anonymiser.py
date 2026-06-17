from collections import defaultdict
from .models import RedactedText

def anonymise(redacted: RedactedText) -> tuple[str, dict[str, str]]:
    mapping: dict[str, str] = {}
    entity_order = sorted(redacted.entities, key=lambda e: e.start)
    type_counter: dict[str, int] = defaultdict(int)
    occurrence_mapping = []
    for entity in entity_order:
        type_counter[entity.entity_type] += 1
        n = type_counter[entity.entity_type]
        placeholder = f"[{entity.entity_type}_{n}]"
        occurrence_mapping.append((entity.placeholder, placeholder))
        mapping[placeholder] = entity.original

    result = redacted.redacted
    for presidio_token, numbered_placeholder in occurrence_mapping:
        result = result.replace(presidio_token, numbered_placeholder, 1)
    return result, mapping

def restore(text: str, mapping: dict[str, str]) -> str:
    for placeholder, original in mapping.items():
        text = text.replace(placeholder, original)
    return text
