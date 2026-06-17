import dataclasses
from .redactor import redact
from .anonymiser import anonymise, restore
from .sentiment import analyse
from .classifier import classify
from .intent import evaluate_intent
from .escalation import check_escalation, HOLDING_MESSAGE
from .llm import call_llm
from .output import assemble

async def process(text: str, session_id: str) -> dict:
    # Stage 1 & 2: PII redaction + anonymisation
    redacted = redact(text)
    anon_text, mapping = anonymise(redacted)

    # Stage 3: raw sentiment (no escalation here)
    sentiment = analyse(text)

    # Stage 4: escalation check (Redis-backed strike system)
    escalation = check_escalation(text, session_id)

    # Stage 5: classifier
    classification = classify(text)

    # Stage 6: intent
    intent = evaluate_intent(text, classification.problem_classes)

    if escalation.skip_llm:
        output = assemble(HOLDING_MESSAGE, sentiment, escalation, classification, intent)
        return dataclasses.asdict(output)

    # Stage 7: LLM call on anonymised text (with any escalation probe in system prompt)
    llm_response_anon = await call_llm(anon_text, escalation.system_prompt_addon)
    llm_response = restore(llm_response_anon, mapping)

    # Stage 8: assemble output
    output = assemble(llm_response, sentiment, escalation, classification, intent)
    return dataclasses.asdict(output)
