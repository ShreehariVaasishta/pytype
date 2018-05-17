"""Initializes and checks the environment needed to run pytype."""

from __future__ import print_function

import os
import sys

from pytype.pytd import typeshed
from pytype.tools import runner
from pytype.tools import utils


def check_pytype_or_die():
  if not runner.can_run("pytype", "-h"):
    print("Cannot run pytype. Check that it is installed and in your path")
    sys.exit(1)


def check_python_version(exe, required):
  """Check if exe is a python executable with the required version."""
  try:
    # python --version outputs to stderr for earlier versions
    _, out, err = runner.BinaryRun([exe, "--version"]).communicate()  # pylint: disable=unpacking-non-sequence
    version = out or err
    version = version.decode("utf-8")
    if version.startswith("Python %s" % required):
      return True, None
    else:
      return False, version.rstrip()
  except OSError:
    return False, "Could not run"


def check_python_exe_or_die(required):
  """Check if a python executable with the required version is in path."""
  error = []
  for exe in ["python", "python%s" % required]:
    valid, out = check_python_version(exe, required)
    if valid:
      return exe
    else:
      error += ["%s: %s" % (exe, out)]
  print("Could not find a valid python%s interpreter in path:" % required)
  print("--------------------------------------------------------")
  print("\n".join(error))
  sys.exit(1)


def initialize_typeshed_or_die():
  """Initialize a Typeshed object or die.

  Returns:
    An instance of Typeshed()
  """
  try:
    return typeshed.Typeshed()
  except IOError as e:
    print(str(e))
    sys.exit(1)


def compute_pythonpath(filenames):
  """Compute a list of dependency paths."""
  paths = set()
  for f in utils.expand_paths(filenames):
    containing_dir = os.path.dirname(f)
    if os.path.exists(os.path.join(containing_dir, "__init__.py")):
      # If the file's containing directory has an __init__.py, we assume that
      # the file is in a (sub)package. Add the containing directory of the
      # top-level package so that 'from package import module' works.
      package_parent = os.path.dirname(containing_dir)
      while os.path.exists(os.path.join(package_parent, "__init__.py")):
        package_parent = os.path.dirname(package_parent)
      p = package_parent
    else:
      # Otherwise, the file is a standalone script. Add its containing directory
      # to the path so that 'import module_in_same_directory' works.
      p = containing_dir
    paths.add(p)
  # Reverse sorting the paths guarantees that child directories always appear
  # before their parents. To see why this property is necessary, consider the
  # following file structure:
  #   foo/
  #     bar1.py
  #     bar2.py  # import bar1
  #     baz/
  #       qux1.py
  #       qux2.py  # import qux1
  # If the path were [foo/, foo/baz/], then foo/ would be used as the base of
  # the module names in both directories, yielding bar1 (good) and baz.qux1
  # (bad). With the order reversed, we get bar1 and qux1 as expected.
  return sorted(paths, reverse=True)