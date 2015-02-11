from argparse import ArgumentParser, HelpFormatter
import configparser, os, sys, utils, re, json, copy, difflib

# ================================
# Global variables
# ================================

template_filetype = '.bat'
template_filetypes = ['.bat', '.sh']
template_replace_string = {
    'target': '<DIRECTORY>',
    'interpreter': '<INTERPRETER> '   # Note the trailing space
}

# Get the paths of important files
template_path   = os.path.join(os.path.dirname(__file__), '..', 'templates/', 'template' + template_filetype) # todo exclude '/'
config_path     = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
helpfile_path   = os.path.join(os.path.dirname(__file__), '..', 'docs/')
recordfile_path = os.path.join(os.path.dirname(__file__), '..', 'records.json')

config = configparser.ConfigParser()
config.read(config_path)

# ================================
# Manage configuration defaults
# ================================

if not config.has_section('GENERAL'):
    config.add_section('GENERAL')

if not config.has_section('INTERPRETER'):
    config.add_section('INTERPRETER')

if not config.get('GENERAL', 'MagicPrompt', fallback=None):
    config.set('GENERAL', 'MagicPrompt', 'true')

default_dest = config.get('GENERAL', 'DefaultDestination', fallback=None)

# ================================
# Make sure that records.txt exists
# ================================

if not os.path.exists(recordfile_path):
    with open(recordfile_path, 'w') as f:
        f.write('{}')

# ================================
# Commands and helper functions
# ================================

def cmd_do(args):
    # Extract paths
    target_path   = os.path.abspath(args.target_path)
    target_folder = os.path.dirname(target_path)
    dest_folder   = os.path.abspath(args.dest_folder)

    # Extract file name and extension
    (filename, filetype) = os.path.splitext(os.path.basename(target_path))
    filename = args.filename or filename

    # If passed file named 'foo' that doesn't exist, prompt to
    # select the appropriate file (ex: foo.exe, foo.bat, ...)
    if os.path.exists(target_folder) and not os.path.exists(target_path):
        result = choose_file(target_folder, filename, filetype)
        if result is None:
            sys.exit('Selection cancelled.')
        else:
            (filename, filetype) = result
            target_path = os.path.join(target_folder, filename + filetype)

    if not os.path.exists(target_path):
        sys.exit('ERROR: The target file could not be found at ' + target_path)
    if not os.path.isfile(target_path):
        sys.exit('ERROR: The target path does not point to a file.')
    if not os.path.exists(dest_folder):
        sys.exit('ERROR: The destination folder could not be found.')
    if not os.path.isdir(dest_folder):
        sys.exit('ERROR: The destination path does not point to a folder.')

    # Build destination path. Change the extension to match the template.
    dest_path = os.path.join(dest_folder, filename + template_filetype)

    # Determine correct interpreter
    default_interpreter = config.get('INTERPRETER', filetype, fallback=None)

    if args.interpreter == True:
        interpreter = config.get('INTERPRETER', filetype, fallback=None)
    elif args.interpreter:
        interpreter = args.interpreter
    elif default_interpreter:               # implicitly "and not args.interpreter"
        interpreter = default_interpreter
    else:
        interpreter = ''

    if interpreter is None:
        sys.exit('ERROR: Flag -i was passed, but no default interpreter exists for filetype "' + filetype + '".')
    if interpreter and utils.which(interpreter) is None:
        sys.exit('ERROR: Interpreter "' + interpreter + '" could not be found.')

    # Read in template file and insert target path and interpreter
    template = get_template(template_filetype)
    template = template.replace(template_replace_string['target'], target_path)
    template = template.replace(template_replace_string['interpreter'], interpreter + (' ' if interpreter else ''))

    # Check if a file exists at the place we want to save to, and
    # prompt user for confirmation if so.
    write_destination = True
    if os.path.isfile(dest_path):
        message = "File '" + os.path.basename(dest_path) + "' already exists at '" + dest_folder + "'. Overwrite? [y/n]"

        choices = {
            ('y', 'yes'): True,
            ('n', 'no'): False
        }

        write_destination = utils.prompt(message, choices, {'case_insensitive': True})

    # Write resulting file to the destination folder
    if write_destination:
        with open(dest_path, 'w') as f:
            f.write(template)

        add_record_entry(filename + template_filetype, target_path, dest_folder)

    # Save requested options
    if args.save and write_destination:
        save_opts  = {'interpreter': False, 'destination': False}
        args.save = args.save.replace('interpreter', 'i')
        args.save = args.save.replace('destination', 'd')

        if 'i' in args.save and interpreter != default_interpreter:
            save_opts['interpreter'] = True

        if 'd' in args.save and dest_folder != default_dest:
            save_opts['destination'] = True

        if save_opts['interpreter']:
            config.set('INTERPRETER', filetype, interpreter)

        if save_opts['destination']:
            config.set('GENERAL', 'DefaultDestination', dest_folder)

        if save_opts['interpreter'] or save_opts['destination']:
            with open('config.ini', 'w') as f:
                config.write(f)

    # Output results
    if write_destination:
        print('Pathification success!')
    else:
        print('Pathification cancelled.')

    print('  Target:      ' + target_path)
    print('  Destination: ' + dest_path)

def cmd_undo(args):
    print('Command "undo" is not yet implemented.')

def cmd_record(args):
    if args.update:
        (added, deleted) = cmd_record_update(args)

        if args.ls:
            cmd_record_ls(args, added, deleted)
    else:
        cmd_record_ls(args)

def cmd_record_update(args):
    (added, deleted) = update_record()

    add_plural = 'item' if added['count'] == 1 else 'items'
    delete_plural = 'item' if deleted['count'] == 1 else 'items'

    message = 'Records updated. '
    message += str(added['count']) + ' ' + add_plural + ' added, '
    message += str(deleted['count']) + ' ' + delete_plural + ' removed.'

    print(message)

    return (added, deleted)

def cmd_record_ls(args, added = {'count': 0, 'list': []}, deleted = {'count': 0, 'list': []}):
    records = get_record()

    if len(records.keys()) == 0:
        print('Record is empty.')
        return
    else:
        print() # Padding from the above line.

    # Make sure to include destinations even if they contain
    # deleted items but nothing else.
    for val in deleted['list']:
        if val['destination'] not in records.keys():
            records[val['destination']] = {}

    for destination, values in sorted(records.items()):
        print(destination + ':')
        file_list = ''

        # Get the files that were added or deleted from the current dest folder.
        added_files   = [(i['filename'], i['source']) for i in added['list'] if i['destination'] == destination]
        deleted_files = [(i['filename'], i['source']) for i in deleted['list'] if i['destination'] == destination]

        # This bit of shenanigans is to get the dictionary key-value pairs
        # AND the deleted files into the same data structure so we can see what
        # was removed.
        if deleted_files:
            values = list(values.items())
            values.extend(deleted_files)
            values = dict(values)

        # Format things nicely. " status filename  => source"
        column_width = len(max(values.keys(), key=len))
        format_string = ' {0:1} {1:' + str(column_width) + '}  => {2}\n'

        # Iterate over everything and build a nice output string.
        for filename, source in sorted(values.items()):
            if (filename, source) in added_files:
                status = '+'
            elif (filename, source) in deleted_files:
                status = '-'
            else:
                status = ''

            file_list += format_string.format(status, filename, source)

        print(file_list)

def cmd_config(args):
    if args.print_config or (not args.set_option and not args.unset_option):
        with open(config_path, 'r') as f:
            print('\nconfig.ini:\n')
            print('  ' + f.read().replace('\n', '\n  '))
            return

    target_option = args.set_option or [args.unset_option]

    # Parse "section[option]" format
    match = re.match(r"(\w+)(?:\[(.+?)\])?", target_option[0])
    (section, option) = match.group(1, 2)

    # If only one match was made, assume that it was
    # the option and make the section GENERAL.
    if option is None:
        (section, option) = ('GENERAL', section)

    section = section.upper()

    if not config.has_section(section):
        sys.exit('ERROR: Unsupported section "' + section + '" passed.')

    if section == 'INTERPRETER' and option and option[0] != '.':
        option = '.' + option

    if args.unset_option:
        if config.has_option(section, option):
            config.remove_option(section, option)
        else:
            sys.exit('ERROR: Option "' + option + '" does not exist.')
    else:
        value = target_option[1]

        if not option:
            sys.exit('ERROR: Invalid option passed.')
        if option and section == 'INTERPRETER' and utils.which(value) is None:
            sys.exit('ERROR: Interpreter "' + value + '" could not be found.')

        config.set(section, option, value)

    # Save changes to file
    with open('config.ini', 'w') as f:
        config.write(f)

    if args.set_option:
        print('Option set succesfully.')
    else:
        print('Option cleared successfully.')

def cmd_help(args=None):
    if args is None or args.helpfile is None:
        helpfile = os.path.join(helpfile_path, 'general.txt')
    elif args.helpfile + '.txt' in os.listdir(helpfile_path):
        helpfile = os.path.join(helpfile_path, args.helpfile + '.txt')
    else:
        sys.exit('Sorry, no help available for "' + args.helpfile + '".')

    with open(helpfile, 'r') as f:
        print('\n' + f.read())

    sys.exit()

def choose_file(target_folder, filename, filetype):
    files = os.listdir(target_folder)
    magic_prompt = config.getboolean('GENERAL', 'MagicPrompt', fallback=False)

    for i, elem in enumerate(files):
        files[i] = os.path.splitext(elem)

    # Get all files whose base name is the same as the target. If
    # magic_prompt is true then the comparison will only be case-sensitive
    # if the filename contains an uppercase character.
    if (magic_prompt and filename.lower() != filename):
        suggestions = [elem[0] + elem[1] for elem in files if elem[0] == filename]
    else:
        suggestions = [elem[0] + elem[1] for elem in files if elem[0].lower() == filename.lower()]

    if len(suggestions) == 1:
        result = suggestions[0]
    elif suggestions:
        if not filetype:
            message = 'Which ' + filename + ' do you want to pathify?'
        else:
            message = filename + filetype + ' not found. Did you mean:'

        options = {}

        for i, suggestion in enumerate(suggestions):
            message += '\n' + str(i + 1) + ' ' + suggestion
            options[str(i + 1)] = suggestion

        # Prompt user, catching keyboard interrupt
        try:
            result = utils.prompt(message, options, {'catch_interrupt': False})
        except KeyboardInterrupt:
            return None
    else:
        result = filename + filetype

    # Return new file information as (filename, filetype)
    return os.path.splitext(result)

def delete_record(filename, destination):
    records = get_record()

    if destination in records.keys() and filename in records[destination].keys():
        del(records[destination][filename])

    if len(records[destination].keys()) == 0:
        del(records[destination])

    write_record(records)

def get_record():
    with open(recordfile_path, 'r') as f:
        records = json.load(f)

    return records

def add_record_entry(filename, source, destination):
    records = get_record()

    if destination not in records.keys():
        records[destination] = {}

    records[destination][filename] = source
    write_record(records)

def write_record(records):
    with open(recordfile_path, 'w') as f:
        json.dump(records, f)

def update_record():
    records = get_record()
    record_copy = copy.deepcopy(records)

    # Get a list of folders to track based on config settings.
    search_folders = config.get('GENERAL', 'SearchFolders', fallback='')
    search_folders = search_folders.replace('\n', '').split(',')
    search_folders.append(default_dest)

    # Include tracked folders in the search.
    for folder in search_folders:
        if folder not in record_copy.keys():
            record_copy[folder] = {}

    record_copy_keys = list(record_copy.keys())

    added = { 'count': 0, 'list': [] }
    deleted = { 'count': 0, 'list': [] }

    # Detect added files that match the pathify template.
    # By default we check all folders that already contain a
    # pathified file, as well as any of the search_folders.
    for destination in record_copy_keys:
        files = os.listdir(destination)
        files = [os.path.join(destination, elem) for elem in files if os.path.splitext(elem)[1] in template_filetypes]

        for filepath in files:
            with open(filepath, 'r') as f:
                (filename, filetype) = os.path.splitext(os.path.basename(filepath))
                watermark = get_template_watermark(filetype)
                file_content = f.read()

                if destination in records and filename + filetype in records[destination].keys():
                    continue

                if file_content.startswith(watermark):
                    template = get_template(filetype)

                    # Get the text leading up to the directory in the template, and use this
                    # to reverse-engineer the template.
                    match = re.search(r"^(.+)<DIRECTORY>$", template, re.MULTILINE).group(1)
                    source = re.search(r"^" + match + r"(.+)$", file_content, re.MULTILINE).group(1)

                    add_record_entry(filename + filetype, source, destination)

                    added['list'].append({
                        'destination': destination,
                        'filename': filename + filetype,
                        'source': source
                    })

                    added['count'] += 1

    # Detect files that were removed.
    for destination, values in record_copy.items():
        for filename, source in values.items():
            path = os.path.join(destination, filename)

            if not os.path.exists(path):
                delete_record(filename, destination)

                deleted['list'].append({
                    'destination': destination,
                    'filename': filename, # Note that this already includes the filetype.
                    'source': source
                })

                deleted['count'] += 1

    # Return a summary of what's changed.
    return (added, deleted)

def get_template(filetype):
    with open(template_path, 'r') as f:
        template = get_template_watermark(template_filetype) + f.read()

    return template

def get_template_watermark(filetype):
    if filetype == '.bat':
        leader = '@echo off\n' + 'rem'
    elif filetype == '.sh':
        leader = '#'

    return leader + ' This file generated by pathify.py\n\n'

# ================================
# Set up parser
# ================================

parser = ArgumentParser(add_help=False)
subparsers = parser.add_subparsers(dest='cmd')

# Excludes the "usage:" reminder
class MinimalFormatter(HelpFormatter):
    def _format_usage(self, usage, actions, groups, prefix=None):
        return ''

# The config sub-command
config_parser = subparsers.add_parser('config', add_help=False, formatter_class=MinimalFormatter)
config_group = config_parser.add_mutually_exclusive_group()
config_group.add_argument('--set', dest='set_option', nargs=2, const=None)
config_group.add_argument('--unset', dest='unset_option', const=None)
config_parser.add_argument('--print', dest='print_config', action='store_true')
config_parser.set_defaults(func=cmd_config)

# The do command
do_parser = subparsers.add_parser('do', add_help=False, formatter_class=MinimalFormatter)
do_parser.add_argument('target_path', type=str)
do_parser.add_argument('-d', '--destination', dest='dest_folder', type=str, required=(default_dest is None),
        default=default_dest)
do_parser.add_argument('-n', '--name', dest='filename', type=str)
do_parser.add_argument('-i', '--interpreter', dest='interpreter', nargs='?', default=False, const=True)
do_parser.add_argument('-s', '--save', dest='save', type=str, nargs='?', const='id',
        choices=['i', 'd', 'id', 'di', 'interpreter', 'destination'])
do_parser.set_defaults(func=cmd_do)

# The undo command (to be implemented)
undo_parser = subparsers.add_parser('undo', add_help=False, formatter_class=MinimalFormatter)
undo_parser.set_defaults(func=cmd_undo)

# The record command
record_parser = subparsers.add_parser('record', add_help=False, formatter_class=MinimalFormatter)
record_parser.add_argument('--ls', dest='ls', action='store_true')
record_parser.add_argument('-u', '--update', dest='update', action='store_true')
record_parser.set_defaults(func=cmd_record)

# The help command
help_parser = subparsers.add_parser('help', add_help=False, formatter_class=MinimalFormatter)
help_parser.add_argument('helpfile', type=str, nargs='?')
help_parser.set_defaults(func=cmd_help)

# ================================
# Run pathify
# ================================

args = parser.parse_args()

if args.cmd is None:
    cmd_help()
else:
    args.func(args)
