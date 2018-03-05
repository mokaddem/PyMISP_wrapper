class MISPAttribute:
    required_fields = ['attribute_type', 'value']

    def __init__(self, event_id, attribute_type, value, category=None, to_ids=False, comment=None, distribution=None, proposal=False):
        self.attribute_dico = {}
        self.attribute_dico['event_id'] = event_id
        self.attribute_dico['attribute_type'] = attribute_type
        self.attribute_dico['value'] = value
        self.attribute_dico['category'] = category
        self.attribute_dico['comment'] = comment
        self.attribute_dico['distribution'] = distribution

        if to_ids is not None:
            self.attribute_dico['to_ids'] = to_ids
        if proposal is not None:
            self.attribute_dico['proposal'] = proposal

    def get_dico(self):
        return self.attribute_dico

    @staticmethod
    def check_validity(attr_dico):
        return set(attr_dico.keys()).issubset(required_fields)
