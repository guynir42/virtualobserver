"""
Various utility functions and classes
that were not relevant to any specific module.
"""
import os
import sys
import string
import re
import numpy as np
from datetime import datetime, timezone
import dateutil.parser

from inspect import signature
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.time import Time


LEGAL_NAME_RE = re.compile(r"^(?!\d)\w+$")


class OnClose:
    """
    Create an instance of this class so that it
    runs the given function/lambda when it goes
    out of scope.
    This could be useful for removing files,
    deleting things from the DB, and so on.
    It triggers even if there is an exception,
    so it is kind of like a finally block.
    """

    def __init__(self, func):
        if not callable(func):
            raise TypeError("func must be callable")
        self.func = func

    def __del__(self):
        self.func()


def trim_docstring(docstring):
    """
    Remove leading and trailing lines, remove indentation, etc.
    See PEP 257: https://peps.python.org/pep-0257/
    """
    if not docstring:
        return ""
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return "\n".join(trimmed)


def short_docstring(docstring):
    """
    Get the first line of the docstring.
    Assumes the docstring has already been cleared
    of leading new lines and indentation.
    """
    if not docstring:
        return ""

    return docstring.splitlines()[0]


def help_with_class(cls, pars_cls=None, sub_classes=None):
    """
    Print the help for this object and objects contained in it.

    Parameters
    ----------
    cls : class
        The class to print help for.
    pars_cls : class, optional
        The class that contains the parameters for this class.
        If None, no parameters are printed.
    sub_classes : list of classes, optional
        A list of classes that are contained in this class.
        The help for each of those will be printed.
    """
    description = short_docstring(trim_docstring(cls.__doc__))

    print(f"{cls.__name__}\n" "--------\n" f"{description}")

    print_functions(cls)

    if pars_cls is not None:
        print("Parameters:")
        # initialize a parameters object and print it
        pars = pars_cls(cfg_file=False)  # do not read config file
        pars.show_pars()  # show a list of parameters
        print()  # newline

    if sub_classes is not None:
        for sub_cls in sub_classes:
            if hasattr(sub_cls, "help") and callable(sub_cls.help):
                sub_cls.help()
        print()  # newline


def help_with_object(obj, owner_pars):
    """
    Print the help for this object and all sub-objects that know how to print help.
    """
    description = short_docstring(trim_docstring(obj.__class__.__doc__))
    this_pars = None
    print(f"{obj.__class__.__name__}*\n" "--------\n" f"{description}")

    print_functions(obj)

    if hasattr(obj, "pars"):
        print("Parameters:")
        obj.pars.show_pars(owner_pars)
        print()  # newline
        this_pars = obj.pars

    for k, v in obj.__dict__.items():
        if not k.startswith("_"):
            if hasattr(v, "help") and callable(v.help):
                v.help(this_pars)
            elif hasattr(v, "__len__"):
                for li in v:
                    if hasattr(li, "help") and callable(li.help):
                        li.help(this_pars)


def print_functions(obj):
    """
    Print the functions in this object.
    Ignores private methods and help().
    If object doesn't have any public methods
    will print nothing.
    """
    func_list = []
    for name in dir(obj):
        if name.startswith("_") or name == "help":
            continue
        func = getattr(obj, name)
        if callable(func):
            func_list.append(func)

    if len(func_list) > 0:
        print("Methods:")
        for func in func_list:
            print(f"  {func.__name__}{signature(func)}")
        print()


def ra2sex(ra):
    """
    Convert an RA in degrees to a string in sexagesimal format.
    """
    if ra < 0 or ra > 360:
        raise ValueError("RA out of range.")
    ra /= 15.0  # convert to hours
    return f"{int(ra):02d}:{int((ra % 1) * 60):02d}:{((ra % 1) * 60) % 1 * 60:05.2f}"


def dec2sex(dec):
    """
    Convert a Dec in degrees to a string in sexagesimal format.
    """
    if dec < -90 or dec > 90:
        raise ValueError("Dec out of range.")
    return f"{int(dec):+03d}:{int((dec % 1) * 60):02d}:{((dec % 1) * 60) % 1 * 60:04.1f}"


def ra2deg(ra):
    """
    Convert the input right ascension into a float of decimal degrees.
    The input can be a string (with hour angle units) or a float (degree units!).

    Parameters
    ----------
    ra: scalar float or str
        Input RA (right ascension).
        Can be given in decimal degrees or in sexagesimal string (in hours!)
        Example 1: 271.3
        Example 2: 18:23:21.1

    Returns
    -------
    ra: scalar float
        The RA as a float, in decimal degrees

    """
    if type(ra) == str:
        c = SkyCoord(ra=ra, dec=0, unit=(u.hourangle, u.degree))
        ra = c.ra.value  # output in degrees
    else:
        ra = float(ra)

    if not 0.0 < ra < 360.0:
        raise ValueError(f"Value of RA ({ra}) is outside range (0 -> 360).")

    return ra


def dec2deg(dec):
    """
    Convert the input right ascension into a float of decimal degrees.
    The input can be a string (with hour angle units) or a float (degree units!).

    Parameters
    ----------
    dec: scalar float or str
        Input declination.
        Can be given in decimal degrees or in sexagesimal string (in degrees as well)
        Example 1: +33.21 (northern hemisphere)
        Example 2: -22.56 (southern hemisphere)
        Example 3: +12.34.56.7

    Returns
    -------
    dec: scalar float
        The declination as a float, in decimal degrees

    """
    if type(dec) == str:
        c = SkyCoord(ra=0, dec=dec, unit=(u.degree, u.degree))
        dec = c.dec.value  # output in degrees
    else:
        dec = float(dec)

    if not -90.0 < dec < 90.0:
        raise ValueError(f"Value of dec ({dec}) is outside range (-90 -> +90).")

    return dec


def date2jd(date):
    """
    Parse a string or datetime object into a Julian Date (JD) float.
    If string, will parse using dateutil.parser.parse.
    If datetime, will convert to UTC or add that timezone if is naive.
    If given as float, will just return it as a float.

    Parameters
    ----------
    date: float or string or datetime
        The input date or datetime object.

    Returns
    -------
    jd: scalar float
        The Julian Date associated with the input date.

    """
    if isinstance(date, datetime):
        t = date
    elif isinstance(date, str):
        t = dateutil.parser.parse(date)
    else:
        return float(date)

    if t.tzinfo is None:  # naive datetime (no timezone)
        # turn a naive datetime into a UTC datetime
        t = t.replace(tzinfo=timezone.utc)
    else:  # non naive (has timezone)
        t = t.astimezone(timezone.utc)

    return Time(t).jd


def luptitudes(flux, noise_rms):
    """
    Convert fluxes into Luptitude magnitudes.

    Parameters
    ----------
    flux: scalar float or array of floats
        The fluxes to convert.
    noise_rms: scalar float or array of floats
        The RMS noise of the fluxes.

    Returns
    -------
    luptitudes: scalar float or array of floats
        The Luptitude magnitudes.


    ref: https://ui.adsabs.harvard.edu/abs/1999AJ....118.1406L/abstract
    """
    flux = np.asarray(flux)
    noise_rms = np.asarray(noise_rms)
    lup = -2.5 / np.log(10) * (np.arcsinh(flux / (2 * noise_rms)) + np.log(noise_rms))

    return lup


def sanitize_attributes(attr):
    """
    Make sure the attributes that are given do not
    contain any numpy arrays or scalars, and that
    each NaN is turned into None.

    This makes it easier to put the data into the database.
    """
    if isinstance(attr, np.ndarray):
        attr = attr.tolist()
        # no return, recursively iterate through the list:
    if isinstance(attr, list):
        return [sanitize_attributes(a) for a in attr]

    if isinstance(attr, dict):
        new_attr = {}
        for k, v in attr.items():
            new_attr[k] = sanitize_attributes(v)
        return new_attr

    # only scalars beyond this point...
    if attr is None:
        return attr

    if attr is np.nan:
        return None

    # convert numpy scalars to python scalars
    if isinstance(attr, (bool, np.bool_)):
        return bool(attr)

    if issubclass(type(attr), (int, np.integer)):
        return int(attr)

    if issubclass(type(attr), (float, np.floating)):
        number = float(attr)
        if np.isnan(number):
            number = None
        return number

    return attr


def unit_convert_bytes(units):
    """
    Convert a number of bytes into another unit.
    Can choose "kb", "mb", or "gb", which will return
    the appropriate number of bytes in that unit.
    If "bytes" or any other string, will return 1,
    i.e., no conversion.
    """
    if units.endswith("s"):
        units = units[:-1]

    return {
        "byte": 1,
        "kb": 1024,
        "mb": 1024**2,
        "gb": 1024**3,
    }.get(units.lower(), 1)


def is_scalar(value):
    """
    Check if a value is a scalar (string or not has __len__).
    Returns True if a scalar, False if not.
    """
    if isinstance(value, str) or not hasattr(value, "__len__"):
        return True
    else:
        return False


def add_alias(att):
    return property(
        fget=lambda self: getattr(self, att),
        fset=lambda self, value: setattr(self, att, value),
        doc=f'Alias for "{att}"',
    )


def legalize(name, to_lower=False):
    """
    Turn a given name for a project/observatory into a legal name.
    This trims whitespace, replaces inner spaces and dashes with underscores,
    and pushes name up to upper case.
    This allows some freedom when giving the name of the project/observatory
    to various search methods.
    All these names should be saved after being legalized, so they can be
    searched against a legalized version of the user input.

    Parameters
    ----------
    name: str
        The name to be legalized.
    to_lower: bool
        If True, will convert to lower case instead of upper case. Default is False.

    """

    name = name.strip()
    name = name.replace(" ", "_").replace("-", "_")
    if to_lower:
        name = name.lower()
    else:
        name = name.upper()

    if re.match(LEGAL_NAME_RE, name) is None:
        raise ValueError(f'Cannot legalize name "{name}". Must be alphanumeric without a leading number. ')

    return name


def random_string(length=16):
    """
    Generate a string of given length,
    made of random letters.
    """
    letters = list(string.ascii_lowercase)
    return "".join(np.random.choice(letters, length))


def find_file_ignore_case(filename, folders=None):
    """
    Try to locate a file in a case-insensitive manner.
    If filename is not an absolute path,
    will search the current folder.
    If specifying folders as a list or string,
    will search those folders instead.
    To list the current folder use ".".

    Parameters
    ----------
    filename: str
        The filename to search for.
    folders: list or str
        The folders to search in. If not specified,
        will search the current folder.
        To list the current folder use ".".

    Returns
    -------
    path: str
        The full path to the file, if found.
        If not found, will return None.
    """
    if os.path.isabs(filename):
        folders, filename = os.path.split(filename)

    if folders is None:
        folders = ["."]
    elif isinstance(folders, str):
        folders = [folders]

    for folder in folders:
        if not os.path.isdir(folder):
            raise ValueError(f"Cannot find folder {folder}.")
        files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        # reverse alphabetical order but with lower case before upper case
        files.sort(reverse=True)

        for file in files:
            if file.lower() == filename.lower():
                return os.path.abspath(os.path.join(folder, file))

    return None


def load_altdata(attrs):
    """
    Load the altdata for a given object,
    that has been saved into an HDF5 store's attributes.
    This includes the different ways we can save the altdata,
    like as a simple dictionary or as `altdata_keys` and
    then individual values for those keys as separate attributes.

    Parameters
    ----------
    attrs: dict or tables.attributeset.AttributeSet
        The attributes of the HDF5 store.

    Returns
    -------
    altdata: dict
        The altdata dictionary.
    """
    if "altdata" in attrs:
        return attrs["altdata"]

    if "altdata_keys" in attrs:
        altdata = {}
        for key in attrs["altdata_keys"]:
            altdata[key] = attrs[key]
        return altdata


class NamedList(list):
    """
    A list of objects, each of which has
    a "name" attribute.
    This list can be indexed by name,
    and also using numerical indices.
    """

    def __init__(self, ignorecase=False):
        self.ignorecase = ignorecase
        super().__init__()

    def convert_name(self, name):
        # TODO: maybe replace with legalize?
        if self.ignorecase:
            return name.lower()
        else:
            return name

    def __getitem__(self, index):
        if isinstance(index, str):
            index_l = self.convert_name(index)
            num_idx = [self.convert_name(item.name) for item in self].index(index_l)
            return super().__getitem__(num_idx)
        elif isinstance(index, int):
            return super().__getitem__(index)
        else:
            raise TypeError(f"index must be a string or integer, not {type(index)}")

    def __contains__(self, name):
        return self.convert_name(name) in [self.convert_name(item.name) for item in self]

    def keys(self):
        return [item.name for item in self]


class UniqueList(list):
    """
    A list that checks if an appended object is already part of the list.

    If appending or setting one of the elements,
    all elements of the list are checked against the new
    object, using the list of comparison_attributes specified.
    """

    def __init__(self, comparison_attributes=[], ignorecase=False):
        self.comparison_attributes = comparison_attributes
        if len(comparison_attributes) == 0:
            self.comparison_attributes = ["name"]
        self.ignorecase = ignorecase

        super().__init__()

    def __setitem__(self, key, value):
        for i in range(len(self)):
            if i != key:
                if self._check(value, self[i]):
                    raise ValueError(f"Cannot assign to index {key}, with duplicate in index {i}.")
        super().__setitem__(key, value)

    def __getitem__(self, key):
        if isinstance(key, int):
            return super().__getitem__(key)
        elif isinstance(key, (list, tuple, np.ndarray)):
            shortlist = [item for item in self]
            for i, attr in enumerate(self.comparison_attributes):
                if i >= len(key):
                    break  # no more keys to check
                shortlist = [item for item in shortlist if self._compare(key[i], getattr(item, attr))]

            if i == len(key) - 1:
                return shortlist[0]
            else:
                new_list = UniqueList(self.comparison_attributes[i:])
                new_list.extend(shortlist)
                return new_list

        elif isinstance(key, str):
            shortlist = [item for item in self if self._compare(key, getattr(item, self.comparison_attributes[0]))]
            if len(shortlist) == 0:
                raise KeyError(f"Key {key} not found in list.")
            if len(self.comparison_attributes) == 1:
                return shortlist[0]
            else:
                new_list = UniqueList(self.comparison_attributes[1:])
                new_list.extend(shortlist)
                return new_list

        else:
            raise TypeError(f"index must be a string or integer, not {type(key)}")

    def append(self, value):
        self._check_and_remove(value)
        super().append(value)

    def extend(self, value):
        for v in value:
            self._check_and_remove(v)
        super().extend(value)

    def plus(self, value):
        self.extend(value)

    def _check_and_remove(self, value):
        """
        Removes from the list all instances that
        are the same as "value", using the _check function.
        """
        # go over list in reverse in case some get popped out
        for i in range(len(self)).__reversed__():
            if self._check(value, self[i]):
                self.pop(i)

    def _check(self, value, other):
        """
        Check if the value is the same as the other object.
        Only if all the comparison_attributes are the same,
        the check returns True. If any are different, returns False.
        """
        for att in self.comparison_attributes:
            if not self._compare(getattr(value, att), getattr(other, att)):
                return False

        return True

    def _compare(self, key1, key2):
        """
        Check if the two keys are the same.
        If ignorecase is True, will convert to lower case.
        """
        if self.ignorecase and isinstance(key1, str) and isinstance(key2, str):
            return key1.lower() == key2.lower()
        else:
            return key1 == key2


class CircularBufferList(list):
    """
    A list that behaves like a circular buffer.
    When appending to the list, if the list is full,
    the first element is removed and the new element
    is appended to the end.
    """

    def __init__(self, size):
        self.size = size
        self.total = 0  # how many insertions have been made, ever
        super().__init__()

    def append(self, value):
        if len(self) == self.size:
            self.pop(0)
        super().append(value)
        self.total += 1

    def extend(self, value):
        self.total += len(value)
        super().extend(value)
        self[:] = self[-self.size :]

    def plus(self, value):
        self.extend(value)
