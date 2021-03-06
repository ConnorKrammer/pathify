# --------------------------------------------------------
# Credit goes to Preet Kukreti for which()
# See the original at http://stackoverflow.com/a/18547150
# --------------------------------------------------------

import os
import sys
import stat
import tempfile


def is_case_sensitive_filesystem():
    tmphandle, tmppath = tempfile.mkstemp()
    is_insensitive = os.path.exists(tmppath.upper())
    os.close(tmphandle)
    os.remove(tmppath)
    return not is_insensitive

_IS_CASE_SENSITIVE_FILESYSTEM = is_case_sensitive_filesystem()

def which(program, case_sensitive=_IS_CASE_SENSITIVE_FILESYSTEM):
    """ Simulates unix `which` command. Returns absolute path if program found """
    def is_exe(fpath):
        """ Return true if fpath is a file we have access to that is executable """
        accessmode = os.F_OK | os.X_OK
        if os.path.exists(fpath) and os.access(fpath, accessmode) and not os.path.isdir(fpath):
            filemode = os.stat(fpath).st_mode
            ret = bool(filemode & stat.S_IXUSR or filemode & stat.S_IXGRP or filemode & stat.S_IXOTH)
            return ret

    def list_file_exts(directory, search_filename=None, ignore_case=True):
        """ Return list of (filename, extension) tuples which match the search_filename"""
        if ignore_case:
            search_filename = search_filename.lower()
        for root, dirs, files in os.walk(path):
            for f in files:
                filename, extension = os.path.splitext(f)
                if ignore_case:
                    filename = filename.lower()
                if not search_filename or filename == search_filename:
                    yield (filename, extension)
            break

    fpath, fname = os.path.split(program)

    # is a path: try direct program path
    if fpath:
        if is_exe(program):
            return program
    elif "win" in sys.platform:
        # isnt a path: try fname in current directory on windows
        if is_exe(fname):
            return program

    paths = [path.strip('"') for path in os.environ.get("PATH", "").split(os.pathsep)]
    exe_exts = [ext for ext in os.environ.get("PATHEXT", "").split(os.pathsep)]
    if not case_sensitive:
        exe_exts = map(str.lower, exe_exts)

    # try append program path per directory
    for path in paths:
        exe_file = os.path.join(path, program)
        if is_exe(exe_file):
            return exe_file

    # try with known executable extensions per program path per directory
    for path in paths:
        filepath = os.path.join(path, program)
        for extension in exe_exts:
            exe_file = filepath+extension
            if is_exe(exe_file):
                return exe_file

    # try search program name with "soft" extension search
    if len(os.path.splitext(fname)[1]) == 0:
        for path in paths:
            file_exts = list_file_exts(path, fname, not case_sensitive)
            for file_ext in file_exts:
                filename = "".join(file_ext)
                exe_file = os.path.join(path, filename)
                if is_exe(exe_file):
                    return exe_file

    return None

def prompt(prompt, choices={}, options={}):
    defaultOptions = {
        'case_insensitive': False,
        'restrict_choices': True,
        'catch_interrupt': True,
        'list_delimiter': None
    }

    # Merge passed options with defaults.
    options = dict(list(defaultOptions.items()) + list(options.items()))

    # Keep requesting input while user responses are invalid
    # User can cancel by sending a keyboard interrupt (CTRL-C on Windows)
    result = None
    while result == None:
        print(prompt)

        try:
            response = input('=> ')
            print() # print an empty line
        except KeyboardInterrupt:
            if options['catch_interrupt']:
                break
            else:
                raise

        # Expand the contents of tuple and list keys into individual keys
        if choices:
            for key, value in choices.copy().items():
                if type(key) == tuple or type(key) == list:
                    choices.pop(key)

                    for i in key:
                        choices[i] = value

        # Make input and option keys case-insensitive
        if options['case_insensitive']:
            response = response.lower()

            for key, value in choices.copy().items():
                del choices[key]
                choices[key.lower()] = value

        # Parse response as a list if it uses the delimiter
        # If invalid and 'restrict_choices' is set, prompt again.
        if options['list_delimiter'] is not None:
            response_list = response.split(options['list_delimiter'])
            invalid_choice = False
            result = []

            # Here we build a list of results based on the parsed response.
            # If any of the choices are invalid, break the loop and re-prompt.
            # This is a more complicated version of the single-argument case below.
            for response in response_list:
                if response in choices.keys():
                    result.append(choices[response])
                elif choices and options['restrict_choices']:
                    print("Response '" + response + "' is not a valid choice.")
                    invalid_choice = True
                    result = None
                    break
                else:
                    result.append(response)

            if invalid_choice:
                continue
        else:
            if response in choices.keys():
                result = choices[response]
            elif choices and options['restrict_choices']:
                print("Response '" + response + "' is not a valid choice.")
                continue
            else:
                result = response

    # Let the user know they cancelled successfully.
    if result == None:
        print('Selection cancelled.')

    return result

