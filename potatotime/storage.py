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
    TEMPLATE_USER = "potatotime_user_{user_id}.json"
    TEMPLATE_CLIENT = "potatotime_client_{client_id}.json"

    def has_user_credentials(self, user_id: str) -> bool:
        return os.path.exists(self.TEMPLATE_USER.format(user_id=user_id))

    def get_user_credentials(self, user_id: str) -> Dict:
        if self.has_user_credentials(user_id):
            with open(self.TEMPLATE_USER.format(user_id=user_id)) as f:
                return f.read()

    def save_user_credentials(self, user_id: str, credentials: str):
        # TODO: json.dumps here, to be consistent?
        with open(self.TEMPLATE_USER.format(user_id=user_id), 'w') as f:
            f.write(credentials)

    def get_client_credentials(self, client_id: str):
        with open(self.TEMPLATE_CLIENT.format(client_id=client_id)) as f:
            return f.read()


class EnvStorage(Storage):
    """
    Environment variables for holding credentials. Note that writes are not
    supported.
    """
    TEMPLATE_USER = "POTATOTIME_USER_{user_id}"
    TEMPLATE_CLIENT = "POTATOTIME_CLIENT_{client_id}"

    def has_user_credentials(self, user_id: str) -> bool:
        return self.TEMPLATE_USER.format(user_id=user_id) in os.environ

    def get_user_credentials(self, user_id: str) -> Dict:
        return os.environ.get(self.TEMPLATE_USER.format(user_id=user_id), '{}')

    def save_user_credentials(self, user_id: str, credentials: str):
        raise NotImplementedError('Writes are not implemented for EnvStorage')

    def get_client_credentials(self, client_id: str):
        return os.environ.get(self.TEMPLATE_CLIENT.format(client_id=client_id), '{}')
