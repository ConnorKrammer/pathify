from argparse import ArgumentParser, HelpFormatter
import configparser, os, sys, utils, re

# ================================
# Global variables
# ================================

# Get the paths of important files
templatePath = os.path.join(os.path.dirname(__file__), '../templates/', 'template.bat')
configPath   = os.path.join(os.path.dirname(__file__), '../', 'config.ini')
helpFilePath = os.path.join(os.path.dirname(__file__), '../', 'docs/')

config = configparser.ConfigParser()
config.read(configPath)

# ================================
# Commands and helper functions
# ================================

def cmd_do(args):
    # Extract paths
    targetPath   = os.path.abspath(args.targetPath)
    targetFolder = os.path.dirname(targetPath)
    destFolder   = os.path.abspath(args.destFolder)

    # Extract file name and extension
    (filename, filetype) = os.path.splitext(os.path.basename(targetPath))
    filename = args.filename or filename

    # If passed file named 'foo' that doesn't exist, prompt to
    # select the appropriate file (ex: foo.exe, foo.bat, ...)
    if os.path.exists(targetFolder) and not os.path.exists(targetPath):
        result = chooseFile(targetFolder, filename, filetype)
        if result is None:
            sys.exit('Selection cancelled.')
        else:
            (filename, filetype) = result
            targetPath = os.path.join(targetFolder, filename + filetype)

    if not os.path.exists(targetPath):
        sys.exit('ERROR: The target file could not be found at ' + targetPath)
    if not os.path.isfile(targetPath):
        sys.exit('ERROR: The target path does not point to a file.')
    if not os.path.exists(destFolder):
        sys.exit('ERROR: The destination folder could not be found.')
    if not os.path.isdir(destFolder):
        sys.exit('ERROR: The destination path does not point to a folder.')

    # Build destination path. Change the extension to match the template.
    destPath = os.path.join(destFolder, filename) + os.path.splitext(templatePath)[1]

    # Determine correct interpreter
    defaultInterpreter = config.get('INTERPRETER', filetype, fallback=None)

    if args.interpreter == True:
        interpreter = config.get('INTERPRETER', filetype, fallback=None)
    elif args.interpreter:
        interpreter = args.interpreter
    elif defaultInterpreter:               # implicitly "and not args.interpreter"
        interpreter = defaultInterpreter
    else:
        interpreter = ''

    if interpreter is None:
        sys.exit('ERROR: Flag -i was passed, but no default interpreter exists for filetype "' + filetype + '".')
    if interpreter and utils.which(interpreter) is None:
        sys.exit('ERROR: Interpreter "' + interpreter + '" could not be found.')

    # Read in template file and fill target path and interpreter
    with open(templatePath, 'r') as f:
        template = f.read()
        template = template.replace('<DIRECTORY>', targetPath)
        template = template.replace('<INTERPRETER> ', interpreter + (' ' if interpreter else ''))

    # Check if a file exists at the place we want to save to, and
    # prompt user for confirmation if so.
    writeDestination = True
    if os.path.isfile(destPath):
        message = "File '" + os.path.basename(destPath) + "' already exists at '" + destFolder + "'. Overwrite? [y/n]"

        choices = {
            ('y', 'yes'): True,
            ('n', 'no'): False
        }

        writeDestination = utils.prompt(message, choices, {'case_insensitive': True})

    # Write resulting file to the destination folder
    if writeDestination:
        with open(destPath, 'w') as f:
            f.write(template)

    # Save requested options
    if args.save and writeDestination:
        saveOpts  = {'interpreter': False, 'destination': False}
        args.save = args.save.replace('interpreter', 'i')
        args.save = args.save.replace('destination', 'd')

        if 'i' in args.save and interpreter != defaultInterpreter:
            saveOpts['interpreter'] = True

        if 'd' in args.save and args.destFolder != defaultDest:
            saveOpts['destination'] = True

        if saveOpts['interpreter']:
            config.set('INTERPRETER', filetype, interpreter)

        if saveOpts['destination']:
            config.set('GENERAL', 'DefaultDestination', args.destFolder)

        if saveOpts['interpreter'] or saveOpts['destination']:
            with open('config.ini', 'w') as f:
                config.write(f)

    # Output results
    if writeDestination:
        print('Pathification success!')
    else:
        print('Pathification cancelled.')

    print('  Target:      ' + targetPath)
    print('  Destination: ' + destPath)

def cmd_undo(args):
    print('Command "undo" is not yet implemented.')
    sys.exit()

def cmd_config(args):
    if args.printConfig:
        with open(configPath, 'r') as f:
            print('\nconfig.ini:\n')
            print('  ' + f.read().replace('\n', '\n  '))
            sys.exit()

    targetOption = args.setOption or [args.unsetOption]

    # Parse "section[option]" format
    m = re.match(r"(\w+)(?:\[(.+?)\])?", targetOption[0])
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

    if args.unsetOption:
        if config.has_option(section, option):
            config.remove_option(section, option)
        else:
            sys.exit('ERROR: Option "' + option + '" does not exist.')
    else:
        value = targetOption[1]

        if not option:
            sys.exit('ERROR: Invalid option passed.')
        if option and section == 'INTERPRETER' and utils.which(value) is None:
            sys.exit('ERROR: Interpreter "' + value + '" could not be found.')

        config.set(section, option, value)

    # Save changes to file
    with open('config.ini', 'w') as f:
        config.write(f)

    if args.setOption:
        print('Option set succesfully.')
    else:
        print('Option cleared successfully.')

    sys.exit()

def cmd_help(args=None):
    if args is None or args.helpFile is None:
        helpFile = os.path.join(helpFilePath, 'general.txt')
    elif args.helpFile in ['do', 'undo', 'config', 'help']:
        helpFile = os.path.join(helpFilePath, args.helpFile + '.txt')
    else:
        sys.exit('Sorry, no help available for "' + args.helpFile + '".')

    with open(helpFile, 'r') as f:
        print('\n' + f.read())

    sys.exit()

def chooseFile(targetFolder, filename, filetype):
    files = os.listdir(targetFolder)
    magicPrompt = config.getboolean('GENERAL', 'MagicPrompt', fallback=False)

    for i, elem in enumerate(files):
        files[i] = os.path.splitext(elem)

    # Get all files whose base name is the same as the target. If
    # magicPrompt is true then the comparison will only be case-sensitive
    # if the filename contains an uppercase character.
    if (magicPrompt and filename.lower() != filename):
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

defaultDest = config.get('GENERAL', 'DefaultDestination', fallback=None)

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
configParser = subparsers.add_parser('config', add_help=False, formatter_class=MinimalFormatter)
configGroup = configParser.add_mutually_exclusive_group(required=True)
configGroup.add_argument('--set', dest='setOption', nargs=2, const=None)
configGroup.add_argument('--unset', dest='unsetOption', const=None)
configGroup.add_argument('--print', dest='printConfig', action='store_true')
configParser.set_defaults(func=cmd_config)

# The do command
doParser = subparsers.add_parser('do', add_help=False, formatter_class=MinimalFormatter)
doParser.add_argument('targetPath', type=str)
doParser.add_argument('-d', '--destination', dest='destFolder', type=str, required=(defaultDest is None),
        default=defaultDest)
doParser.add_argument('-n', '--name', dest='filename', type=str)
doParser.add_argument('-i', '--interpreter', dest='interpreter', nargs='?', default=False, const=True)
doParser.add_argument('-s', '--save', dest='save', type=str, nargs='?', const='id',
        choices=['i', 'd', 'id', 'di', 'interpreter', 'destination'])
doParser.set_defaults(func=cmd_do)

# The undo command (to be implemented)
undoParser = subparsers.add_parser('undo', add_help=False, formatter_class=MinimalFormatter)
undoParser.set_defaults(func=cmd_undo)

# The help command
helpParser = subparsers.add_parser('help', add_help=False, formatter_class=MinimalFormatter)
helpParser.add_argument('helpFile', type=str, nargs='?')
helpParser.set_defaults(func=cmd_help)

# ================================
# Run pathify
# ================================

args = parser.parse_args()

# If no command, print help. Otherwise, run the command.
if args.cmd is None:
    cmd_help()
else:
    args.func(args)
