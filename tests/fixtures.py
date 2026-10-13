from core.models import Campaign, DraftBatch


def campaign(**overrides):
    values = dict(sender_name='Aditi', sender_company='Design Studio', product='Landing page design',
                  usp='Collaborative design with clear milestones', audience='Independent online retailers',
                  pain_point='Visitors may struggle to find product details', objective='Ask permission to share a sample')
    values.update(overrides)
    return Campaign(**values)


def batch_data():
    return {'drafts': [
        {'strategy': 'Value-first', 'subject': 'A clearer product introduction',
         'body': 'Hello, I am Aditi from Design Studio. We offer collaborative landing page design with clear milestones. Could I share a sample? Best, Aditi',
         'call_to_action': 'Could I share a sample?'},
        {'strategy': 'Problem-solution', 'subject': 'Helping visitors find the right details',
         'body': 'If visitors find product information difficult to locate, a focused landing page could help explain your offer. Would an example be useful? Regards, Aditi at Design Studio',
         'call_to_action': 'Would an example be useful?'},
        {'strategy': 'Permission-based', 'subject': 'May I send a design example?',
         'body': 'Hi, our team designs pages for independent online retailers. Rather than a lengthy introduction, may I send an overview? No pressure if the timing is not right. Aditi, Design Studio',
         'call_to_action': 'may I send an overview?'},
    ]}


def batch():
    return DraftBatch.model_validate(batch_data())
