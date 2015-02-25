# Todo

## Current

1. Write code documentation.
2. Print output if a tracked directory or the default directory isn't in the
   user's PATH. Allow appending them automatically.
    - use os.environ['PATH'].append('something')
    - it's tricky to test reliably whether a directory is in the user's PATH
3. Change some variable names to be clearer.
4. Refactoring, unit tests.
5. Tidy list delimiter handling in utils.py, if possible.
6. Make consistent whether output starts with a blank line or not.

## On Hold:

1. Make templates for the different shell scripting languages (bash, ...)
   so that pathify can produce scripts that work in any shell. This should
   auto-detect the shell but be able to be overridden with a configuration
   option.
