from argparse import ArgumentParser, HelpFormatter
import configparser, os, sys, utils, re

# Get the paths of important files
templatePath = os.path.join(os.path.dirname(__file__), '../templates/', 'template.bat')
configPath   = os.path.join(os.path.dirname(__file__), '../', 'config.ini')
helpFilePath = os.path.join(os.path.dirname(__file__), '../', 'helpfile.txt')

# Parse defaults
config = configparser.ConfigParser()
config.read(configPath)

# If INTERPRETER section doesn't exist, create it
if not config.has_section('GENERAL'):
    config.add_section('GENERAL')
if not config.has_section('INTERPRETER'):
    config.add_section('INTERPRETER')

# If a default destination is specified, don't require the -d option
defaultDest  = config.get('GENERAL', 'DestinationFolder', fallback=None)
destRequired = defaultDest is None

# Parse arguments
parser = ArgumentParser(add_help=False)
subparsers = parser.add_subparsers()

# Excludes the "usage:" reminder
class MinimalFormatter(HelpFormatter):
    def _format_usage(self, usage, actions, groups, prefix=None):
        return ''

# The config sub-command
configParser = subparsers.add_parser('config', add_help=False, formatter_class=MinimalFormatter)
configGroup = configParser.add_mutually_exclusive_group(required=True)
configGroup.add_argument('--set', dest='setOption', nargs=2, const=None)
configGroup.add_argument('--unset', dest='unsetOption', const=None)

# group.add_argument('--setopt', dest='setOption', nargs=2)

# The main arguments
group = parser.add_mutually_exclusive_group()
group.add_argument('-h', '--help', dest='printHelp', action='store_true')
group.add_argument('targetPath', type=str, nargs='?')
parser.add_argument('-d', '--destination', dest='destFolder', type=str, required=destRequired, default=defaultDest)
parser.add_argument('-n', '--name', dest='filename', type=str)
parser.add_argument('-i', '--interpreter', dest='interpreter', nargs='?', default=False, const=True)
parser.add_argument('--save', dest='save', type=str, nargs='?', const='id',
        choices=['i', 'd', 'id', 'di', 'interpreter', 'destination'])

args = parser.parse_args()
args.setOption = args.setOption if hasattr(args, 'setOption') else False
args.unsetOption = args.unsetOption if hasattr(args, 'unsetOption') else False
args.targetOption = args.setOption or [args.unsetOption]

# Print help text and exit
if args.printHelp:
    with open(helpFilePath, 'r') as f:
        print(f.read())
    sys.exit()

# Set provided options and exit
if args.targetOption:

    # Parse "section[option]" format
    m = re.match(r"(\w+)(?:\[(.+?)\])?", args.targetOption[0])
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
        value = args.targetOption[1]

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

# Extract paths
targetPath   = os.path.abspath(args.targetPath)
targetFolder = os.path.dirname(targetPath)
destFolder   = os.path.abspath(args.destFolder)

# Extract file name and extension
(filename, filetype) = os.path.splitext(os.path.basename(targetPath))
filename = args.filename or filename

# Check if target folder exists
# Fetch all filenames
# Compare filenames without extensions to passed target
# If more than one exist (ex: foo.bat and foo.sh) prompt user to pick one
if os.path.exists(targetFolder) and not os.path.exists(targetPath):
    files = os.listdir(targetFolder)

    for i, elem in enumerate(files):
        files[i] = os.path.splitext(elem)

    # Get all files whose base name is the same as the target
    suggestions = [elem[0] + elem[1] for elem in files if elem[0] == filename]

    if suggestions:
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
            sys.exit('Selection cancelled.')

        # Change path details to match new target
        (filename, filetype) = os.path.splitext(result)
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
        config.set('GENERAL', 'destinationfolder', args.destFolder)

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
