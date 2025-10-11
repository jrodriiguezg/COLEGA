import json
import os

class ContactManager:
    """Gestiona la lista de contactos."""
    def __init__(self, data_file='contacts.json'):
        self.data_file = data_file
        self.contacts = self._load_contacts()

    def _load_contacts(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return []
        return []

    def _save_contacts(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.contacts, f, indent=4)

    def add_contact(self, name, phone, relation=None):
        """Añade un nuevo contacto."""
        new_contact = {'name': name, 'phone': phone, 'relation': relation}
        self.contacts.append(new_contact)
        self._save_contacts()

    def find_contact(self, name_query):
        """Busca contactos por nombre."""
        name_query = name_query.lower()
        return [c for c in self.contacts if name_query in c['name'].lower()]

    def get_all_contacts(self):
        """Devuelve todos los contactos."""
        return self.contacts