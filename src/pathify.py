from argparse import ArgumentParser, HelpFormatter
import configparser, os, sys, utils, re

# ================================
# Global variables
# ================================

# Get the paths of important files
template_path = os.path.join(os.path.dirname(__file__), '../templates/', 'template.bat')
config_path   = os.path.join(os.path.dirname(__file__), '../', 'config.ini')
helpfile_path = os.path.join(os.path.dirname(__file__), '../', 'docs/')

config = configparser.ConfigParser()
config.read(config_path)

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
    dest_path = os.path.join(dest_folder, filename) + os.path.splitext(template_path)[1]

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

    # Read in template file and fill target path and interpreter
    with open(template_path, 'r') as f:
        template = f.read()
        template = template.replace('<DIRECTORY>', target_path)
        template = template.replace('<INTERPRETER> ', interpreter + (' ' if interpreter else ''))

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

    # Save requested options
    if args.save and write_destination:
        save_opts  = {'interpreter': False, 'destination': False}
        args.save = args.save.replace('interpreter', 'i')
        args.save = args.save.replace('destination', 'd')

        if 'i' in args.save and interpreter != default_interpreter:
            save_opts['interpreter'] = True

        if 'd' in args.save and args.dest_folder != default_dest:
            save_opts['destination'] = True

        if save_opts['interpreter']:
            config.set('INTERPRETER', filetype, interpreter)

        if save_opts['destination']:
            config.set('GENERAL', 'DefaultDestination', args.dest_folder)

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
    sys.exit()

def cmd_config(args):
    if args.print_config:
        with open(config_path, 'r') as f:
            print('\nconfig.ini:\n')
            print('  ' + f.read().replace('\n', '\n  '))
            sys.exit()

    target_option = args.set_option or [args.unset_option]

    # Parse "section[option]" format
    m = re.match(r"(\w+)(?:\[(.+?)\])?", target_option[0])
    (section, option) = m.group(1, 2)

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

    sys.exit()

def cmd_help(args=None):
    if args is None or args.helpfile is None:
        helpfile = os.path.join(helpfile_path, 'general.txt')
    elif args.helpfile in ['do', 'undo', 'config', 'help']:
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
config_group = config_parser.add_mutually_exclusive_group(required=True)
config_group.add_argument('--set', dest='set_option', nargs=2, const=None)
config_group.add_argument('--unset', dest='unset_option', const=None)
config_group.add_argument('--print', dest='print_config', action='store_true')
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

# The help command
help_parser = subparsers.add_parser('help', add_help=False, formatter_class=MinimalFormatter)
help_parser.add_argument('helpfile', type=str, nargs='?')
help_parser.set_defaults(func=cmd_help)

# ================================
# Run pathify
# ================================

args = parser.parse_args()

# If no command, print help. Otherwise, run the command.
if args.cmd is None:
    cmd_help()
else:
    args.func(args)
