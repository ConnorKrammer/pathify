# Pathify.py

## What is Pathify?

Pathify adds an executable file to the system PATH by dynamically creating
a batch file to run it from a location that is already under the system
PATH. By doing so, developers can specify single executables to be added
to the PATH (instead of everything within the PATH), can execute scripts
by specifying a desired interpreter, and all without adding an extra
directory to the PATH environment variable.

## Features

1. Keep your PATH clean by specifying single executables instead of whole
   directories.
2. Allow executing scripts by specifying an interpreter to be used,
   allowing you to lock a particular script to a particular interpreter
   version, all while saving typing from the command line.
3. Add an executable to your PATH incredibly quickly. Just
   `pathify path/to/target` and you're done!
4. Set different versions of the same executable to use different names.
   Use Python 3 *and* Python 2? `pathify python.exe -n python3` to set up
   the pathified Python to be called from the command line with `python3`.
