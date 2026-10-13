"""Small, explicit contracts for user input and generated content."""
import hashlib
import re
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Tone(str, Enum):
    PROFESSIONAL = 'Professional'
    FRIENDLY = 'Friendly'
    PERSUASIVE = 'Persuasive'
    FORMAL = 'Formal'
    CONCISE = 'Concise'


class Length(str, Enum):
    SHORT = 'Short'
    MEDIUM = 'Medium'
    DETAILED = 'Detailed'


WORD_LIMITS = {Length.SHORT: 100, Length.MEDIUM: 160, Length.DETAILED: 240}


class Strategy(str, Enum):
    VALUE = 'Value-first'
    PROBLEM = 'Problem-solution'
    PERMISSION = 'Permission-based'


class Campaign(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    sender_name: str = Field(min_length=1, max_length=100)
    sender_company: str = Field(min_length=1, max_length=150)
    product: str = Field(min_length=3, max_length=500)
    usp: str = Field(min_length=3, max_length=500)
    audience: str = Field(min_length=3, max_length=300)
    recipient_name: str = Field(default='', max_length=100)
    recipient_company: str = Field(default='', max_length=150)
    pain_point: str = Field(min_length=3, max_length=600)
    objective: str = Field(min_length=3, max_length=300)
    facts: str = Field(default='', max_length=2000)
    tone: Tone = Tone.PROFESSIONAL
    length: Length = Length.SHORT

    def fingerprint(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class Draft(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    strategy: Strategy
    subject: str = Field(min_length=3, max_length=140)
    body: str = Field(min_length=20, max_length=5000)
    call_to_action: str = Field(min_length=3, max_length=300)

    @model_validator(mode='after')
    def one_line_subject(self):
        if '\n' in self.subject or '\r' in self.subject:
            raise ValueError('Subject must be a single line.')
        return self


class DraftBatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    drafts: list[Draft] = Field(min_length=3, max_length=3)

    @model_validator(mode='after')
    def distinct_strategies(self):
        if {draft.strategy for draft in self.drafts} != set(Strategy):
            raise ValueError('Use all three distinct strategies.')
        bodies = [set(re.findall(r'\w+', draft.body.casefold())) for draft in self.drafts]
        for i in range(3):
            for j in range(i):
                overlap = len(bodies[i] & bodies[j]) / max(1, len(bodies[i] | bodies[j]))
                if overlap > 0.85:
                    raise ValueError('Drafts are too similar. Please generate again.')
        return self


class FollowUp(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    subject: str = Field(min_length=3, max_length=140)
    body: str = Field(min_length=20, max_length=2000)

    @model_validator(mode='after')
    def validate_follow_up(self):
        if '\n' in self.subject or '\r' in self.subject:
            raise ValueError('Subject must be a single line.')
        if len(self.body.split()) > 90:
            raise ValueError('Follow-up exceeds 90 words.')
        engagement = (
            r"\byou(?:['’]ve|\s+(?:have|had))?"
            r"(?:\s+(?:already|recently|probably|may have|might have|must have))?"
            r"\s+(?:opened|read|responded|replied)\b"
            r"|\b(?:thanks|thank you)\s+for\s+(?:your\s+)?"
            r"(?:reply|response|responding|reading|getting back)\b"
            r"|\byour\s+(?:reply|response)\s+(?:to|about)\b"
        )
        if re.search(engagement, self.body, re.I):
            raise ValueError('Follow-up implies recipient engagement.')
        return self


def edited_email(subject: str, body: str) -> tuple[str, str]:
    """Validate human edits before export or a follow-up request."""
    subject, body = subject.strip(), body.strip()
    if not 3 <= len(subject) <= 140 or '\n' in subject or '\r' in subject:
        raise ValueError('Use a single-line subject between 3 and 140 characters.')
    if not 20 <= len(body) <= 5000:
        raise ValueError('Use an email body between 20 and 5,000 characters.')
    return subject, body


def email_fingerprint(subject: str, body: str) -> str:
    return hashlib.sha256(f'{subject}\n{body}'.encode()).hexdigest()


def claim_warnings(campaign: Campaign, text: str) -> list[str]:
    """Flag new numeric claims; this is a review aid, not a fact checker."""
    supplied = campaign.model_dump_json()
    new_numbers = set(re.findall(r'\b\d+(?:[.,]\d+)*(?:%)?', text)) - set(
        re.findall(r'\b\d+(?:[.,]\d+)*(?:%)?', supplied)
    )
    if new_numbers:
        return ['This draft contains numbers absent from your inputs. Check them before use.']
    return []
