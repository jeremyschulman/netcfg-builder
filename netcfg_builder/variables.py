# -----------------------------------------------------------------------------
# System Imports
# -----------------------------------------------------------------------------

from typing import Optional
from functools import wraps
from operator import itemgetter
from pathlib import Path
from importlib.machinery import SourceFileLoader
from itertools import chain

# -----------------------------------------------------------------------------
# Public Imports
# -----------------------------------------------------------------------------

import envtoml
import envyaml

# -----------------------------------------------------------------------------
#
#                                 CODE BEGINS
#
# -----------------------------------------------------------------------------


MAX_PRIORITY = 10

_registered_loaders = list()


def ingest(priority: Optional[int] = MAX_PRIORITY):
    if not (0 <= priority < MAX_PRIORITY):
        raise ValueError(f"priority must [0 .. {MAX_PRIORITY}]: {priority}")

    def decorator(func):
        _registered_loaders.append((priority, func))

        @wraps(func)
        def wrapper(tvars: dict, **kwargs):
            func(tvars, **kwargs)

        return wrapper

    return decorator


def load_variables(**extra_vars) -> dict:
    tvars = dict()
    _registered_loaders.sort(key=itemgetter(0))
    for prio, var_func in _registered_loaders:
        var_func(tvars, **extra_vars)

    return tvars


def load_sourcefile(py_file: Path):
    """
    This function will load all of the python modules found in the given cfg_dir
    so that any User defined plugins are brought into the system and registered.
    """
    mod_name = py_file.stem
    try:
        SourceFileLoader(mod_name, str(py_file)).load_module(mod_name)

    except Exception as exc:
        raise RuntimeError(f"Unable to load python file: {str(py_file)}: {str(exc)}")

    # try:
    #     breakpoint()
    #     finder = FileFinder(str(py_file.parent), (SourceFileLoader, [".py"]))
    #     mod_name = py_file.stem
    #     finder.find_spec(mod_name).loader.load_module(mod_name)
    # except Exception as exc:
    #     raise RuntimeError(f"Unable to load python file: {str(py_file)}: {str(exc)}")


def load_directory(dir_path: Path):
    all_vars = dict()

    for var_file in dir_path.glob("*.toml"):
        all_vars.update(envtoml.load(var_file.open()))

    globs = (dir_path.glob(f"*.{ext}") for ext in ("json", "yml", "yaml"))

    for var_file in chain.from_iterable(globs):
        all_vars.update(envyaml.EnvYAML(str(var_file)))

    return all_vars
