import json
import os

from bakker.storage import FileSystemStorage


class Config:
    """
    Config class provides methods to deal with configuration file for Bakker. 
    
    Enables the ability to create, save, and read the ``config.json`` file. Can also read, write, and modify individual JSON key-value pairs in the configuration file.
    """
    USER_DIR = os.path.expanduser('~')
    CONFIG_FILE = os.path.join(USER_DIR, '.bakker/config.json')

    def __init__(self):
        """
        Opens up the configuration file in read mode, loading it into the ``config`` variable. If the file does not exist, the config variable is initialized as an empty JSON object.
        """
        if os.path.isfile(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def _save(self):
        """
        Writes config variable to the JSON file.
        """
        if not os.path.exists(os.path.dirname(self.CONFIG_FILE)):
            os.makedirs(os.path.dirname(self.CONFIG_FILE))
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(self.config, f)

    def __setitem__(self, key, value):
        """
        Sets individual items in the ``config`` variable.

        :param key: The key for which the ``value`` is to be updated.
        :param value: The value to be put into the given ``key``.
        """
        assert isinstance(value, str)

        keys = key.split('.')
        current = self.config
        for key in keys[:-1]:
            current = current.setdefault(key, {})
        current[keys[-1]] = value
        self._save()

    def __getitem__(self, key):
        """
        Returns the value stored in given ``key`` inside ``config``.

        This method works by splitting the given ``key`` on the dot-operator ``.`` to traverse the JS object. Iteratively sets the ``current`` variable as its own ``key`` to reach the needed node. 

        :param key: The variable whose value is needed.

        :raises KeyError: If the node reached is not a string, in which case it is not a key but a value.
        """
        keys = key.split('.')
        current = self.config
        for key in keys:
            current = current[key]
        if not isinstance(current, str):
            raise KeyError()
        return current

    def __delitem__(self, key):
        """
        Deletes the given ``key`` and all the stored values inside it, subsequently saving the configuration.

        :param key: The variable which is to be deleted.
        """
        def del_dict_item(d, keys):
            """
            Recursively deletes the ``keys`` from a given dictionary ``d``.

            :param d: Dictionary from which the deletion is to be done.
            :param keys: The keys which need to be deleted from the dictionary.
            """
            if len(keys) > 1:
                del_dict_item(d[keys[0]], keys[1:])
                if len(d[keys[0]]) == 0:
                    del d[keys[0]]
            else:
                del d[keys[0]]

        keys = key.split('.')
        del_dict_item(self.config, keys)
        self._save()

    def __contains__(self, key):
        """
        Checks if the given ``key`` exists in the ``config`` variable.

        Returns true if it does, and false otherwise. Uses ``__getitem__`` method to identify if the given ``key`` is present or not.

        :param key: The variable whose existence needs to be verified.
        """
        try:
            self.__getitem__(key)
            return True
        except KeyError:
            return False

    def items(self):
        """
        @TODO: the ultimate purpose of this method.
        """
        def build_items(d, prefix):
            """
            Recursively traverses the dictionary.
            """
            for key, value in d.items():
                next_prefix = prefix + '.' + key if prefix is not None else key
                if isinstance(value, dict):
                    yield from build_items(value, next_prefix)
                elif isinstance(value, str):
                    yield next_prefix, value
        return build_items(self.config, None)


DEFAULT_STORAGE_KEY = 'default.storage'
DEFAULT_STORAGE_CHOICES = ['fs']
STORAGE_FILE_SYSTEM_PATH = 'storage.file_system.path'
