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

When declaring filenames, you can tag them with `mkdir=True`. Whenever a
filename that is tagged in this manner is accessed, the parent directory will
be created if it doesn't exist yet.
>>> import os.path
>>> fname = FileNames()
>>> fname.add('my_file', 'path/to/file1', mkdir=True)
>>> os.path.exists(fname.my_file.parent)
True

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

When many of your filenames contain the same placeholders, it may be convenient to
pre-fill the placeholder once with `fname.fill_placeholder(placeholder=value)`, after
which it will be automatically filled in the future:
>>> fname = FileNames()
>>> fname.add('epochs', 'sub-{subject:02d}_ses-{session:02d}_{cond}-epo.fif')
>>> fname.add('evoked', 'sub-{subject:02d}_ses-{session:02d}_{cond}-ave.fif')
>>> fname.fill_placeholder('subject', 1)
>>> fname.fill_placeholder('session', 2)
>>> fname.evoked(cond='visual')
PosixPath('sub-01_ses-02_visual-ave.fif')

Pre-filled placeholders can still be overwritten by manually specifying them when using
a filename:
>>> fname = FileNames()
>>> fname.add('epochs', 'sub-{subject:02d}-epo.fif')
>>> fname.fill_placeholder('subject', 1)
>>> fname.epochs(subject=2)
PosixPath('sub-02-epo.fif')

You can undo filling in placeholders using `fname.clear_placeholder(placeholder)`, after
which it will again need to be filled in manually when using the filename.
>>> fname = FileNames()
>>> fname.add('epochs', 'sub-{subject:02d}-epo.fif')
>>> fname.fill_placeholder('subject', 1)
>>> fname.clear_placeholder('subject')
>>> fname.epochs()
Traceback (most recent call last):
   ...
ValueError: Cannot construct filename, because these parameters are missing: {'subject'}

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

The returned filenames are of type `pathlib.Path`, which offers a bunch of
convenience methods related to filenames that you wouldn't get with ordinary
strings. They can be used in all locations were you would otherwise use a
string filename. However, if you want an ordinary string, there are several ways of
doing so. One is to cast the filename to a string:
>>> fname = FileNames()
>>> fname.add('my_file', '/path/to/file1')
>>> str(fname.my_file)
'/path/to/file1'

Another way is to, when adding a filename, to specify that the filename should always be
returned as string:
>>> fname = FileNames()
>>> fname.add('my_file', '/path/to/file1', as_str=True)
>>> fname.my_file
'/path/to/file1'

If you want all of your filenames to be strings, always, then you can pass
`as_str=True` when creating the `FileNames` object:
>>> fname = FileNames(as_str=True)
>>> fname.add('my_file', '/path/to/file1')
>>> fname.my_file
'/path/to/file1'

Obviously this also works when the filename contains placeholders:
>>> fname = FileNames(as_str=True)
>>> fname.add('my_file', '/path/to/file{subject:d}')
>>> fname.add('my_file', '/path/to/file{subject:d}')
>>> fname.my_file(subject=1)
'/path/to/file1'

The filenames object should be pickleable as long as you don't use custom functions to
generate the filenames:
>>> import pickle
>>> fname = FileNames()
>>> fname.add('normal_file', 'path/to/file1')
>>> fname.add('template', 'path/to/{bla}')
>>> len(pickle.dumps(fname))
267

Author: Marijn van Vliet <w.m.vanvliet@gmail.com>
"""

import difflib
import string
from pathlib import Path


class FileNames(object):
    """Utility class to manage filenames.

    See the help of the filenames python module for details.

    Parameters
    ----------
    as_str : bool

    """

    def __init__(self, as_str: bool = False):
        self.as_str = as_str
        self._files = dict()
        self._with_mkdir = dict()
        self._pre_filled = dict()

    def files(self):
        """Obtain a list of file aliases known to this FileNames object.

        Returns
        -------
        files : list of str
            The list of file aliases.

        """
        return sorted(self._files.keys())

    def add(self, alias, fname, mkdir=False, as_str=False):
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
        as_str : bool
            Whether to return the filename as a string or as a pathlib.Path object.

        See Also
        --------
        add_from_dict

        """
        if callable(fname):
            self._add_function(alias, fname, mkdir, as_str)
        else:
            # Determine whether the string contains placeholders and whether
            # all placeholders can be pre-filled with existing file aliases.
            placeholders = _get_placeholders(fname)
            if len(placeholders) == 0:
                self._add_fname(alias, fname, mkdir, as_str)  # Plain string filename
            else:
                prefilled = _prefill_placeholders(placeholders, self._files, dict())
                if len(prefilled) == len(placeholders):
                    # The template could be completely pre-filled. Add the
                    # result as a plain string filename.
                    self._add_fname(
                        alias, Path(fname.format(**prefilled)), mkdir, as_str
                    )
                else:
                    # Add filename as a template
                    self._add_template(alias, fname, mkdir, as_str)

    def add_from_dict(self, fname_dict, mkdir=False, as_str=False):
        """Add all entries from an {alias: fname} dictionary.

        Parameters
        ----------
        fname_dict : dict
            A dictionary containing filename aliases as the keys and the full
            filename as a value. Filenames can either be a string, optionally
            containing placeholders, or a function. If the filename is a
            function, it will get called with the FileNames object as first
            parameter, followed by any parameters that were supplied along with
            the request.
        mkdir : bool
            Create the parent directory, if it doesn't already exist, for the
            file whenever one of these filenames is accessed.
        as_str : bool
            Whether to return the filename as a string or as a pathlib.Path object.

        See Also
        --------
        add

        """
        for alias, fname in fname_dict.items():
            self.add(alias, fname, mkdir, as_str)

    def fill_placeholder(self, placeholder, value):
        """Fill in a placeholder for all filename templates.

        Parameters
        ----------
        placeholder : str
            The name of the placeholder.
        value : any type
            The value for the placeholder.

        See Also
        --------
        clear_placeholder

        """
        self._pre_filled[placeholder] = value

    def clear_placeholder(self, placeholder):
        """Clear a previously filled-in placeholder for all filename templates.

        Parameters
        ----------
        placeholder : str
            The name of the placeholder to clear.

        See Also
        --------
        fill_placeholder

        """
        del self._pre_filled[placeholder]

    def _add_fname(self, alias, fname, mkdir=False, as_str=False):
        """Add a filename that is a plain string."""
        if not as_str and not self.as_str:
            fname = Path(fname)
        if mkdir:
            self._with_mkdir[alias] = fname
        self._files[alias] = fname

    def _add_template(self, alias, template, mkdir=False, as_str=False):
        """Add a filename that is a string containing placeholders."""
        # Construct a function that will do substitution for any placeholders
        # in the template.
        fname = _Template(
            template, self._pre_filled, self._files, as_str or self.as_str, mkdir
        )

        # Bind the fname function to this instance of FileNames
        self._files[alias] = fname

    def _add_function(self, alias, func, mkdir=False, as_str=False):
        """Add a filename that is computed using a user-specified function."""

        # Construct a function that will call the user supplied function with
        # the proper arguments. We prepend 'self' so the user supplied function
        # has easy access to all the filepaths.
        def fname(**kwargs):
            fname = func(self, **kwargs)
            if mkdir:
                Path(str(fname)).parent.mkdir(parents=True, exist_ok=True)
            return str(fname) if (as_str or self.as_str) else fname

        # Bind the fname function to this instance of FileNames
        self._files[alias] = fname

    def __getattr__(self, name):
        """Check whether to do mkdir when accessing plain Path/string."""
        # We need to wrap this in a try/except block because joblib pickling does
        # something weird with __getattr__ that may fail.
        if name in self._files:
            fname = self._files[name]
        else:
            msg = f"Unknown filename: '{name}'"
            matches = difflib.get_close_matches(name, self.files(), 1)
            if len(matches) == 1:
                msg += f" (did you mean '{matches[0]}'?)"
            raise AttributeError(msg)

        if isinstance(fname, _Template) and fname._all_placeholders_prefilled():
            fname = fname()

        if name in self._with_mkdir:
            self._with_mkdir[name].parent.mkdir(parents=True, exist_ok=True)

        return fname


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
    return [
        p[1]
        for p in string.Formatter().parse(template)
        if p[1] is not None and len(p[1]) > 0
    ]


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
            if not isinstance(path, (str, Path)):
                try:
                    path = path(**user_values)
                except ValueError:
                    # Placeholder could not be pre-filled given the supplied
                    # values by the user.
                    continue
                except TypeError:
                    continue

            # Add the path as possible placeholder value
            placeholder_values[placeholder] = path

    return placeholder_values


class _Template:
    """Function that performs variable substitution  returns the file path."""

    def __init__(self, template, pre_filled, files, as_str, mkdir):
        self.template = template
        self.pre_filled = pre_filled
        self.files = files
        self.as_str = as_str
        self.mkdir = mkdir

    def __call__(self, **kwargs):
        """Make a filename from a template.

        Any placeholders that point to known file aliases will be prefilled. The
        rest is filled given the values provided by the user when requesting the
        filename.

        Parameters
        ----------
        kwargs : dict
            The key=value parameters that the user specified when requesting the
            filename.

        Returns
        -------
        filename : str
            The filename, obtained by filling all the placeholders of the template
            string.

        """
        # Get all placeholder names
        placeholders = _get_placeholders(self.template)

        # Pre-fill placeholders based on existing file aliases
        placeholder_values = _prefill_placeholders(placeholders, self.files, kwargs)

        # Pre-fill placeholders based on explicitly pre-filled values
        placeholder_values.update(**self.pre_filled)

        # Add user specified values for the placeholders
        placeholder_values.update(**kwargs)

        # Check whether all placeholder values are now properly provided.
        provided = set(placeholder_values.keys())
        needed = set(placeholders)
        missing = needed - provided
        if len(missing) > 0:
            raise ValueError(
                "Cannot construct filename, because these parameters are missing: "
                f"{missing}"
            )

        # Do the substitution
        fname = self.template.format(**placeholder_values)
        if not self.as_str:
            fname = Path(fname)
            if self.mkdir:
                fname.parent.mkdir(parents=True, exist_ok=True)
        elif self.mkdir:
            Path(fname).parent.mkdir(parents=True, exist_ok=True)
        return fname

    def _all_placeholders_prefilled(self):
        """Check if all placeholders can be pre-filled."""
        # Get all placeholder names
        placeholders = _get_placeholders(self.template)

        # Pre-fill placeholders based on existing file aliases
        placeholder_values = _prefill_placeholders(placeholders, self.files, {})

        # Pre-fill placeholders based on explicitly pre-filled values
        placeholder_values.update(**self.pre_filled)

        # Check whether all placeholder values are now properly provided.
        provided = set(placeholder_values.keys())
        needed = set(placeholders)
        missing = needed - provided
        return len(missing) == 0
