import os
from typing import Dict
import json
from abc import ABC, abstractmethod


class Storage(ABC):
    @abstractmethod
    def has_user_credentials(self, user_id: str) -> bool:
        pass

    @abstractmethod
    def get_user_credentials(self, user_id: str) -> Dict:
        pass

    @abstractmethod
    def save_user_credentials(self, user_id: str, credentials: str):
        pass

    @abstractmethod
    def get_client_credentials(self, client_id: str):
        pass


class FileStorage(Storage):
    TEMPLATE = "{user_id}.json"

    def has_user_credentials(self, user_id: str) -> bool:
        return os.path.exists(self.TEMPLATE.format(user_id=user_id))

    def get_user_credentials(self, user_id: str) -> Dict:
        if self.has_user_credentials(user_id):
            with open(self.TEMPLATE.format(user_id=user_id)) as f:
                return json.loads(f.read())
            
    def save_user_credentials(self, user_id: str, credentials: str):
        # TODO: json.dumps here, to be consistent?
        with open(self.TEMPLATE.format(user_id=user_id), 'w') as f:
            f.write(credentials)

    def get_client_credentials(self, client_id: str):
        with open(self.TEMPLATE.format(user_id=client_id)) as f:
            return json.loads(f.read())