def MISPAttribute(event_id, attribute_type, value, category=None, to_ids=False, comment=None, distribution=None, proposal=False):
    attribute_dico = {}
    attribute_dico['event_id'] = event_id
    attribute_dico['value'] = value
    attribute_dico['attribute_type'] = attribute_type
    attribute_dico['category'] = category
    attribute_dico['comment'] = comment
    attribute_dico['distribution'] = distribution

    if to_ids is not None:
        attribute_dico['to_ids'] = to_ids
    if proposal is not None:
        attribute_dico['proposal'] = proposal

    return attribute_dico
