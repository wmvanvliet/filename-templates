filenames
=========

Make filenames from string templates.
This package exposes the `FileNames` class, which keeps a list of filenames and provides a wrapper around `string.format` with some bells and whisles to make the syntax super nice.

I wrote this to keep track of filenames during data analysis projects, where there are many files, which names follow a standard pattern. For example: `data-day001.csv data-day002.csv data-day003.csv`. Processing these files may produce: `data-day001-processed.csv data-day002-processed.csv data-day003-processed.csv`. In these cases, it is good practice to define the templates for these filenames once, for example in a configuration file, and re-use them in the different analysis scripts.


Installation
------------
either through pip:

    pip install https://api.github.com/repos/wmvanvliet/filenames/zipball/master

or from the repository:

    python setup.py install

To run the tests:

    python setup.py test


Usage
-----
Use the `add` method to add new filenames. You specify a short "alias" for
them, which you can use to retrieve the full filename later:

    fname = FileNames()
    fname.add('my_file', '/path/to/file1')
    fname.my_file
    '/path/to/file1'

Filenames can also be templates that can be used to generate
filenames for different subjects, conditions, etc.:

    >>> fname = FileNames()
    >>> fname.add('epochs', '/data/{subject}/{cond}-epo.fif')
    >>> fname.epochs(subject='sub001', cond='face')
    '/data/sub001/face-epo.fif'

Templates can contain placeholders in the way
[`string.format`](https://docs.python.org/3/library/string.html#formatstrings)
allows, including formatting options:

    >>> fname = FileNames()
    >>> fname.add('epochs', '/data/sub{subject:03d}/{cond}-epo.fif')
    >>> fname.epochs(subject=1, cond='face')
    '/data/sub001/face-epo.fif'

If a placeholder happens to be the alias of a file that has been added earlier,
the placeholder is automatically filled:

    >>> fname = FileNames()
    >>> fname.add('subjects', '/data/subjects_dir')
    >>> fname.add('epochs', '{subjects}/{subject}/{cond}-epo.fif')
    >>> fname.epochs(subject='sub001', cond='face')
    '/data/subjects_dir/sub001/face-epo.fif'

If all placeholders could be automatically filled, no brackets () are required
when accessing it:

    >>> fname = FileNames()
    >>> fname.add('subjects', '/data/subjects_dir')
    >>> fname.add('fsaverage', '{subjects}/fsaverage-src.fif')
    >>> fname.fsaverage
    '/data/subjects_dir/fsaverage-src.fif'

If computing the file path gets more complicated than the cases above, you can
supply your own function. When the filename is requested, your function will
get called with the FileNames object as first parameter, followed by any
parameters that were supplied along with the request:

    >>> fname = FileNames()
    >>> fname.add('basedir', '/data/subjects_dir')
    >>> def my_function(files, subject):
    ...     if subject == 1:
    ...         return files.basedir + '/103hdsolli.fif'
    ...     else:
    ...         return files.basedir + '/%s.fif' % subject
    >>> fname.add('complicated', my_function)
    >>> fname.complicated(subject=1)
    '/data/subjects_dir/103hdsolli.fif'


Author
------
Marijn van Vliet <w.m.vanvliet@gmail.com>
