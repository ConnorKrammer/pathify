Todo
====

1. Make templates for the different shell scripting languages (bash, ...)
   so that pathify can produce scripts that work in any shell. This should
   auto-detect the shell but be able to be overridden with a configuration
   option.
2. Write code documentation.
3. Print output if a tracked directory or the default directory isn't in the
   user's PATH. Allow appending them automatically.
    - use os.environ['PATH'].append('something')
4. Change some occurrences of 'destination' to be more semantically
   correct; right now it doesn't always make sense.
5. Structure update loop so that fetching records is always up to date
6. Refactoring, unit tests

