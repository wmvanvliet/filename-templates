"""Utility class to manage a list of filenames.

Use the `add` method to add new filenames. You specify a short "alias" for
them, which you can use to retrieve the full filename later:

>>> from filename_templates import FileNames
>>> fname = FileNames()
>>> fname.add('my_file', '/path/to/file1')
>>> fname.my_file
PosixPath('/path/to/file1')

Filenames can also be templates that can be used to generate
filenames for different subjects, conditions, etc.:

>>> fname = FileNames()
>>> fname.add('epochs', '/data/{subject}/{cond}-epo.fif')
>>> fname.epochs(subject='sub001', cond='face')
PosixPath('/data/sub001/face-epo.fif')

Templates can contain placeholders in the way `string.format` allows,
including formatting options:

>>> fname = FileNames()
>>> fname.add('epochs', '/data/sub{subject:03d}/{cond}-epo.fif')
>>> fname.epochs(subject=1, cond='face')
PosixPath('/data/sub001/face-epo.fif')

If a placeholder happens to be the alias of a file that has been added earlier,
the placeholder is automatically filled:

>>> fname = FileNames()
>>> fname.add('subjects', '/data/subjects_dir')
>>> fname.add('epochs', '{subjects}/{subject}/{cond}-epo.fif')
>>> fname.epochs(subject='sub001', cond='face')
PosixPath('/data/subjects_dir/sub001/face-epo.fif')

If all placeholders could be automatically filled, no brackets () are required
when accessing it:

>>> fname = FileNames()
>>> fname.add('subjects', '/data/subjects_dir')
>>> fname.add('fsaverage', '{subjects}/fsaverage-src.fif')
>>> fname.fsaverage
PosixPath('/data/subjects_dir/fsaverage-src.fif')

The returned filenames are of type ``pathlib.Path``, which offers a bunch of
convenience methods related to filenames that you wouldn't get with ordinary
strings. They can be used in all locations were you would otherwise use a
string filename. However, if you want an ordinary string, there are two ways of
doing so. One is to cast the filename to a string:

>>> fname = FileNames()
>>> fname.add('my_file', '/path/to/file1')
>>> str(fname.my_file)
'/path/to/file1'

If you want all of your filenames to be strings, always, then you can pass
``as_str=True`` when creating the ``FileNames`` object:
>>> fname = FileNames(as_str=True)
>>> fname.add('my_file', '/path/to/file1')
>>> fname.my_file
'/path/to/file1'

Obviously this also works when the filename contains placeholders:
>>> fname = FileNames(as_str=True)
>>> fname.add('my_file', '/path/to/file{subject:d}')
>>> fname.my_file(subject=1)
'/path/to/file1'

If computing the file path gets more complicated than the cases above, you can
supply your own function. When the filename is requested, your function will
get called with the FileNames object as first parameter, followed by any
parameters that were supplied along with the request:

>>> from pathlib import Path
>>> fname = FileNames()
>>> fname.add('basedir', '/data/subjects_dir')
>>> def my_function(files, subject):
...     if subject == 1:
...         return files.basedir / '103hdsolli.fif'
...     else:
...         return files.basedir / f'{subject}.fif'
>>> fname.add('complicated', my_function)
>>> fname.complicated(subject=1)
PosixPath('/data/subjects_dir/103hdsolli.fif')

When defining functions, you are in complete control over what gets returned
when a user requests a filename. It would be good style if you would check the
`files.as_str` attribute to see if the user is requesting a plain string path
and honor that request if possible.
>>> from pathlib import Path
>>> fname = FileNames(as_str=True)
>>> fname.add('basedir', '/data/subjects_dir')
>>> def my_function(files, subject):
...     if subject == 1:
...         fname =- files.basedir / '103hdsolli.fif'
...     else:
...         fname = files.basedir / f'{subject}.fif'
...     if files.as_str:
...         return str(fname)
...     else:
...         return fname
>>> fname.add('complicated', my_function)
>>> fname.complicated(subject=1)
/data/subjects_dir/103hdsolli.fif'

Instead of adding one filename at a time, you can add a dictionary of them all
at once:
>>> fname = FileNames()
>>> fname_dict = dict(
...     subjects = '/data/subjects_dir',
...     fsaverage = '{subjects}/fsaverage-src.fif',
... )
>>> fname.add_from_dict(fname_dict)
>>> fname.fsaverage
PosixPath('/data/subjects_dir/fsaverage-src.fif')

When declaring filenames, you can tag them with `mkdir=True`. Whenever a
filename that is tagged in this manner is accessed, the parent directory will
be created if it doesn't exist yet.
>>> import os.path
>>> fname = FileNames()
>>> fname.add('my_file', 'path/to/file1', mkdir=True)
>>> os.path.exists(fname.my_file.parent)
True

Author: Marijn van Vliet <w.m.vanvliet@gmail.com>
"""
import string
from pathlib import Path


class FileNames(object):
    """Utility class to manage filenames.

    See the help of the filenames python module for details.

    Parameters
    ----------
    as_str : bool
    """
    def __init__(self, as_str:bool=False):
        self.as_str = as_str
        self._with_mkdir = dict()

    def files(self):
        """Obtain a list of file aliases known to this FileNames object.

        Returns
        -------
        files : list of str
            The list of file aliases.
        """
        files = dict()
        for name, value in self.__dict__.items():
            public_attributes = ['files', 'add', 'as_str']
            if not name.startswith('_') and name not in public_attributes:
                files[name] = value
        return files

    def add(self, alias, fname, mkdir=False):
        """Add a new filename.

        Parameters
        ----------
        alias : str
            A short alias for the full filename. This alias can later be used
            to retrieve the filename. Aliases can not start with '_' or a
            number.
        fname : str | function
            The full filename. Either a string, optionally containing
            placeholders, or a function that will compute the filename. If you
            specify a function, it will get called with the FileNames object as
            first parameter, followed by any parameters that were supplied
            along with the request.
        mkdir : bool
            Create the parent directory, if it doesn't already exist, for this
            file whenever this filename is accessed.

        See also
        --------
        add_from_dict
        """
        if callable(fname):
            self._add_function(alias, fname, mkdir)
        else:
            # Determine whether the string contains placeholders and whether
            # all placeholders can be pre-filled with existing file aliases.
            placeholders = _get_placeholders(fname)
            if len(placeholders) == 0:
                self._add_fname(alias, fname, mkdir)  # Plain string filename
            else:
                prefilled = _prefill_placeholders(placeholders, self.files(),
                                                  dict())
                if len(prefilled) == len(placeholders):
                    # The template could be completely pre-filled. Add the
                    # result as a plain string filename.
                    self._add_fname(alias, Path(fname.format(**prefilled)),
                                    mkdir)
                else:
                    # Add filename as a template
                    self._add_template(alias, fname, mkdir)

    def add_from_dict(self, fname_dict, mkdir=False):
        """Add all entries from an {alias: fname} dictionary.

        Parameters
        ----------
        fname_fict : dict
            A dictionary containing filename aliases as the keys and the full
            filename as a value. Filenames can either be a string, optionally
            containing placeholders, or a function. If the filename is a
            function, it will get called with the FileNames object as first
            parameter, followed by any parameters that were supplied along with
            the request.
        mkdir : bool
            Create the parent directory, if it doesn't already exist, for the
            file whenever one of these filenames is accessed.

        See also
        --------
        add
        """
        for alias, fname in fname_dict.items():
            self.add(alias, fname, mkdir)

    def _add_fname(self, alias, fname, mkdir=False):
        """Add a filename that is a plain string."""
        if not self.as_str:
            fname = Path(fname)
        if mkdir:
            self._with_mkdir[alias] = fname
        else:
            self.__dict__[alias] = fname

    def _add_template(self, alias, template, mkdir=False):
        """Add a filename that is a string containing placeholders."""
        # Construct a function that will do substitution for any placeholders
        # in the template.
        def fname(**kwargs):
            fname = Path(_substitute(template, self.files(), kwargs))
            if mkdir:
                fname.parent.mkdir(parents=True, exist_ok=True)
            return str(fname) if self.as_str else fname

        # Bind the fname function to this instance of FileNames
        self.__dict__[alias] = fname

    def _add_function(self, alias, func, mkdir=False):
        """Add a filename that is computed using a user-specified function."""
        # Construct a function that will call the user supplied function with
        # the proper arguments. We prepend 'self' so the user supplied function
        # has easy access to all the filepaths.
        def fname(**kwargs):
            fname = func(self, **kwargs)
            if mkdir and (isinstance(fname, Path) or isinstance(fname, str)):
                Path(fname).parent.mkdir(parents=True, exist_ok=True)
            return fname

        # Bind the fname function to this instance of FileNames
        self.__dict__[alias] = fname

    def __getattr__(self, name):
        """Check whether to do mkdir when accessing plain Path/string."""
        if name in self._with_mkdir:
            fname = self._with_mkdir[name]
            Path(fname).parent.mkdir(parents=True, exist_ok=True)
            return fname
        else:
            raise AttributeError(f'Unknown filename: {name}')


def _get_placeholders(template):
    """Get all placeholders from a template string.

    Parameters
    ----------
    template : str
        The template string to get the placeholders for.

    Returns
    -------
    placeholders : list of str
        The list of placeholder names that were found in the template string.
    """
    return [p[1] for p in string.Formatter().parse(template)
            if p[1] is not None and len(p[1]) > 0]


def _substitute(template, files, user_values):
    """Makes a filename from a template.

    Any placeholders that point to known file aliases will be prefilled. The
    rest is filled given the values provided by the user when requesting the
    filename.

    Parameters
    ----------
    template : str
        The template string for the filename.
    files : list of str
        A list of file aliases that are already known.
    user_values : dict
        The key=value parameters that the user specified when requesting the
        filename.

    Returns
    -------
    filename : str
        The filename, obtained by filling all the placeholders of the template
        string.
    """
    # Get all placeholder names
    placeholders = _get_placeholders(template)

    # Pre-fill placeholders based on existing file aliases
    placeholder_values = _prefill_placeholders(placeholders, files,
                                               user_values)

    # Add user specified values for the placeholders
    placeholder_values.update(**user_values)

    # Check whether all placeholder values are now properly provided.
    provided = set(placeholder_values.keys())
    needed = set(placeholders)
    missing = needed - provided
    if len(missing) > 0:
        raise ValueError('Cannot construct filename, because the following '
                         'parameters are missing: %s' % missing)

    # Do the substitution
    return template.format(**placeholder_values)


def _prefill_placeholders(placeholders, files, user_values):
    """Search through existing file aliases to pre-fill placeholder values.

    Parameters
    ----------
    placeholders : list of str
        The list of placeholder names that were found in the template string.
    files : list of str
        A list of file aliases that are already known.
    user_values : dict
        The key=value parameters that the user specified when requesting the
        filename. Can be empty if no parameters were specified (yet).

    Returns
    -------
    placeholder_values : dict
        A dictionary containing the values for the placeholders that could be
        pre-filled.
    """
    placeholder_values = dict()

    for placeholder in placeholders:
        if placeholder in files:
            # Placeholder name is a filename, so get the path
            path = files[placeholder]
            if not isinstance(path, Path):
                try:
                    path = path(**user_values)
                except ValueError:
                    # Placeholder could not be pre-filled given the supplied
                    # values by the user.
                    continue

            # Add the path as possible placeholder value
            placeholder_values[placeholder] = path

    return placeholder_values
