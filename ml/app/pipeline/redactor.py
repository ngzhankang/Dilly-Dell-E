import re
from typing import Optional
from .models import PiiEntity, RedactedText

_analyzer = None
_anonymizer = None

def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
        engine = AnalyzerEngine()
        nric = PatternRecognizer(
            supported_entity="NRIC",
            patterns=[Pattern(name="nric", regex=r"\b[STFG]\d{7}[A-Z]\b", score=0.95)],
        )
        engine.registry.add_recognizer(nric)
        _analyzer = engine
    return _analyzer

def _get_anonymizer():
    global _anonymizer
    if _anonymizer is None:
        from presidio_anonymizer import AnonymizerEngine
        _anonymizer = AnonymizerEngine()
    return _anonymizer

_ENTITIES = ["PERSON", "NRIC", "PHONE_NUMBER", "EMAIL_ADDRESS", "LOCATION", "DATE_OF_BIRTH", "CREDIT_CARD"]

def redact(text: str) -> RedactedText:
    from presidio_anonymizer.entities import OperatorConfig
    analyzer = _get_analyzer()
    anonymizer = _get_anonymizer()
    results = analyzer.analyze(text=text, entities=_ENTITIES, language="en")
    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators={"DEFAULT": OperatorConfig("replace", {"new_value": "<{entity_type}>"})},
    )
    entities = [
        PiiEntity(
            entity_type=r.entity_type,
            original=text[r.start:r.end],
            placeholder=f"<{r.entity_type}>",
            start=r.start,
            end=r.end,
        )
        for r in results
    ]
    return RedactedText(original=text, redacted=anonymized.text, entities=entities)
