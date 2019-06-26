from datetime import datetime
import json
import os
import re
import stat

import xxhash

from .utils import datetime_from_iso_format


class TreeNode:
    """
    Provides a base class for various other data storage methods, viz files, directories, and symlinks.
    """
    def __init__(self, name, checksum, permissions):
        """
        Initializes the TreeNode class.

        :param name: Name to initialize.
        :param checksum: Checksum to initialize.
        :param permissions: Permissions to initialize.
        """
        self.name = name
        self.checksum = checksum
        self.permissions = permissions

    def to_dict(self):
        """
        Creates a dictionary equivalent of the given node type. Must be overriden by a child class to use.

        :raises NotImplementedError: on invocation without override.
        """
        raise NotImplementedError()

    @staticmethod
    def build_node(path, name):
        """
        Invokes the respective ``build_node`` method, depending on whether the ``path`` points to a file, directory, or symlink. 

        :params path: Path of data stored. Could be a file, symlink, or a directory.
        :params name: Name of data stored. Could be a file, symlink, or a directory.
        """
        if os.path.islink(path):
            return SymlinkNode.build_node(path, name)
        elif os.path.isfile(path):
            return FileNode.build_node(path, name)
        elif os.path.isdir(path):
            return DirectoryNode.build_node(path, name)
        
        print('Could not backup: ' + path)

    @staticmethod
    def from_dict(d):
        """
        Fetches the name, checksum, and permissions for each of the respective elements of given dictionary.

        Calls the appropriate ``from_dict`` method for a file, symlink, or a directory, respectively. Can be recursively called to repeat the same for dictionary elements.

        :param d: Dictionary containing various properties of the directory/file/symlink.
        """
        if d['type'] == 'directory':
            return DirectoryNode.from_dict(d)
        elif d['type'] == 'file':
            return FileNode.from_dict(d)
        elif d['type'] == 'symlink':
            return SymlinkNode.from_dict(d)

        raise TypeError('Type ' + d['name'] + ' does not exist.')


class DirectoryNode(TreeNode):
    def __init__(self, name, checksum, permissions, children):
        """
        Initializes the DirectoryNode class.

        :params children: children of the given directory.
        
        See TreeNode's ``__init__`` documentation for a description of remaining parameters.
        """
        super().__init__(name, checksum, permissions)
        self.children = children

    def to_dict(self):
        """
        Provides various properties of the directory, packaging them into a dictionary.

        Returns the ``name``, ``checksum``, ``permissions``, ``type``, and the node's children, recursively.
        """
        return {
                'name': self.name,
                'checksum': self.checksum,
                'permissions': self.permissions,
                'children': [child.to_dict() for child in self.children.values()],
                'type': 'directory',
               }

    @staticmethod
    def build_node(path, name):
        """
        Builds a directory node using the given name and fetching the permissions & checksum of the directory at given path.

        Obtains the permission of the directory. Constructs the children of the directory as a dictionary, looping over the contents of the given ``path``. Generates a checksum on the basis of the children of the directory. Returns a ``DirectoryNode`` built with these parameters.
        
        :params path: The directory's path which needs to be made into a node.
        :params name: The name of the directory.
        """
        assert os.path.isdir(path)

        permissions = stat.S_IMODE(os.lstat(path).st_mode)

        children = dict()
        for child_name in os.listdir(path):
            child_path = os.path.join(path, child_name)
            if not os.path.isfile(child_path) and not os.path.isdir(child_path):
                print("Ignored: " + child_path)
                continue
            children[child_name] = TreeNode.build_node(child_path, child_name)

        child_checksums = [children[child_name].checksum for child_name in sorted(children.keys())]
        message = xxhash.xxh64()
        for child_digest in child_checksums:
            message.update(child_digest)
        checksum = message.hexdigest()

        return DirectoryNode(name, checksum, permissions, children)

    @staticmethod
    def from_dict(d):
        """
        Recursively returns ``name``, ``checksum``, ``permissions`` of the directory and its children, recursively.

        :params d: Directory's property dictionary.
        """
        return DirectoryNode(d['name'], d['checksum'], d['permissions'], {child['name']: TreeNode.from_dict(child) for child in d['children']})


class FileNode(TreeNode):
    def to_dict(self):
        """
        Provides various properties of the file to be packaged into a dictionary.

        Returns the ``name``, ``checksum``, ``permissions``, of the file, setting ``type`` as ``file``.
        """
        return {
                'name': self.name,
                'checksum': self.checksum,
                'permissions': self.permissions,
                'type': 'file',
               }

    @staticmethod
    def build_node(path, name):
        """
        Builds a file node using the given name and fetching the permissions & checksum of the file at given path.

        Obtains the permission of the file. Generates a checksum from the contents of the file. Returns a ``FileNode`` built with these parameters.
        
        :params path: The file's path which needs to be made into a node.
        :params name: The name of the file.
        """
        assert os.path.isfile(path)
        assert not os.path.islink(path)

        permissions = stat.S_IMODE(os.lstat(path).st_mode)

        BLOCKSIZE = 65536

        message = xxhash.xxh64()
        with open(path, 'rb') as f:
            file_buffer = f.read(BLOCKSIZE)
            while len(file_buffer) > 0:
                message.update(file_buffer)
                file_buffer = f.read(BLOCKSIZE)
        checksum = message.hexdigest()

        return FileNode(name, checksum, permissions)

    @staticmethod
    def from_dict(d):
        """
        Returns ``name``, ``checksum``, ``permissions`` of the file.

        :params d: File's property dictionary.
        """
        return FileNode(d['name'], d['checksum'], d['permissions'])


class SymlinkNode(TreeNode):
    def to_dict(self):
        """
        Provides various properties of the symlink to be packaged into a dictionary.

        Returns the ``name``, ``checksum``, ``permissions``, of the symlink, setting ``type`` as ``symlink``.
        """
        return {
                'name': self.name,
                'checksum': self.checksum,
                'permissions': self.permissions,
                'type': 'symlink',
               }

    @staticmethod
    def build_node(path, name):
        """
        Builds a symlink node using the given name and fetching the permissions & checksum of the symlink at given path.

        Obtains the permission of the symlink. Generates a checksum from the contents of the path pointed to by the link. Returns a ``SymlinkNode`` built with these parameters.
        
        :params path: The symlink's path which needs to be made into a node.
        :params name: The name of the symlink.
        """
        assert os.path.islink(path)

        permissions = stat.S_IMODE(os.lstat(path).st_mode)

        message = xxhash.xxh64()
        message.update(os.readlink(path))
        checksum = message.hexdigest()

        return SymlinkNode(name, checksum, permissions)

    @staticmethod
    def from_dict(d):
        """
        Returns ``name``, ``checksum``, ``permissions`` of the symlink.

        :params d: Symlink's property dictionary.
        """
        return SymlinkNode(d['name'], d['checksum'], d['permissions'])


class Checkpoint:
    """
    Checkpoint class 
    """
    def __init__(self, root, time=None, name=None):
        """
        Initializes a Checkpoint object using given parameters.

        :params root: The root on which a suitable ``node`` is to be built.
        :params time: Initializes time as either given value or the current time.
        :params name: Name for the ``Checkpoint`` object. Defaults to ``None``.
        """
        assert name is None or re.match('^[a-zA-Z0-9_\-.]+$', name)

        self.root = root
        self.time = datetime.now() if time is None else time
        self.name = name

    @property
    def meta(self):
        """
        Returns ``Checkpoint``'s metadata using a ``CheckpointMeta`` class.
        """
        return CheckpointMeta(self.root.checksum, self.time, self.name)

    def to_json(self):
        """
        Dumps the ``Checkpoint`` into a JSON string.
        """
        return json.dumps(dict(root=self.root.to_dict(), time=self.time.isoformat(), name=self.name), indent=2)

    def iter(self):
        """
        Iterates over the root of the Checkpoint, entering the directories iteratively in a LIFO manner.
        """
        stack = [(self.root, '')]
        while len(stack):
            current_node, current_path = stack.pop()
            yield current_node, current_path

            if isinstance(current_node, DirectoryNode):
                for child_name, child_node in current_node.children.items():
                    stack.append((child_node, os.path.join(current_path, child_name)))

    @staticmethod
    def build_checkpoint(path, name=None):
        """
        Builds a ``Checkpoint`` object using constructed root node at given path, and the given name.

        :params path: Path whose node is to be constructed for the checkpoint.
        :params name: Name of checkpoint. Defaults to ``None``.
        """
        root = TreeNode.build_node(path, '')
        return Checkpoint(root, name=name)

    @staticmethod
    def from_json(json_str):
        """
        Builds a ``Checkpoint`` from a given JSON string.

        :param json_str: JSON string to be loaded.
        """
        tree_dict = json.loads(json_str)

        return Checkpoint(TreeNode.from_dict(tree_dict['root']), time=datetime_from_iso_format(tree_dict['time']), name=tree_dict['name'])


class CheckpointMeta:
    """
    Provides supporting metadata structure and methods for Checkpoints.
    """
    def __init__(self, checksum, time, name):
        """
        Initializes the CheckpointMeta object with the following parameters.

        :param checksum: Checksum value of 
        :param time:
        :param name:
        """
        self.checksum = checksum
        self.time = time
        self.name = name

    def to_string(self):
        """
        Converts ``checksum`` and ``time`` into an underscore-separated name for ``Checkpoint``s.
        """
        timestring = self.time.isoformat()
        timestring += '.000000' if len(timestring) == 19 else ''

        return self.checksum + '_' + timestring  + ('_' + self.name if self.name else '')

    @staticmethod
    def from_string(string):
        """
        Builds a ``CheckpointMeta`` object from the ``checksum`` and ``time`` provided by its underscore-separated name.

        :params string: Name of the ``Checkpoint``.
        """
        boom = string.split('_', 2)
        checksum = boom[0]
        time = datetime_from_iso_format(boom[1])
        name = None if len(boom) == 2 else boom[2]
        return CheckpointMeta(checksum, time, name)
