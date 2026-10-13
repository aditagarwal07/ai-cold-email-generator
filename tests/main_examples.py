"""Synthetic fixtures, not evidence of real AI responses."""
import json
from pitchcraft import Draft


def campaign(**changes):
    result = dict(sender='Alex', company='Example Studio', offer='Project planning templates',
                  difference='Editable sections with clear task ownership', audience='Small project teams',
                  recipient='', recipient_company='', pain='Planning tasks may feel disorganized',
                  objective='Ask permission to share a sample', facts='', tone='Professional', length='Short')
    result.update(changes)
    return result


def draft_dicts():
    return [
        dict(strategy='Benefit-led', subject='A clearer way to plan a project',
             body='Hello, I am Alex from Example Studio. We offer editable planning templates with clear task ownership. Could I share a sample? Best, Alex',
             call_to_action='Could I share a sample?'),
        dict(strategy='Problem-aware', subject='Keeping project tasks organized',
             body='If your team finds planning tasks difficult to organize, a reusable template may help clarify responsibilities. Would an example be useful? Regards, Alex at Example Studio',
             call_to_action='Would an example be useful?'),
        dict(strategy='Permission-first', subject='May I send a planning template?',
             body='Hi, our studio creates templates for small project teams. Rather than a lengthy introduction, may I send an overview? No pressure if this is not relevant right now. Alex, Example Studio',
             call_to_action='may I send an overview?'),
    ]


def response_json():
    return json.dumps({'drafts': draft_dicts()})


def drafts():
    return [Draft(**value) for value in draft_dicts()]
