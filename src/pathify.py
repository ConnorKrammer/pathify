import argparse
import configparser
import os
import sys
import utils

# Get path to important files
templatePath = os.path.join(os.path.dirname(__file__), '../templates/', 'template.bat')
configPath   = os.path.join(os.path.dirname(__file__), '../', 'config.ini')

# Parse defaults
config = configparser.ConfigParser()
config.read(configPath)

# If a default destination is specified, don't require the -d option
defaultDest  = config.get('DEFAULT', 'DestinationFolder', fallback=None)
destRequired = defaultDest == None

# If INTERPRETER section doesn't exist, create it
if not config.has_section('INTERPRETER'):
    config.add_section('INTERPRETER')

# Parse arguments
parser = argparse.ArgumentParser(description='Creates a .bat file that redirects to a target executable.\n' +
                                             'Useful for selectively adding programs to the PATH environment variable.',
                                 formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('targetPath',
                  type=str,
                  help='The target executable.\n\n',
                  metavar='TARGET')

parser.add_argument('-d', '--destination',
                  type=str,
                  required=destRequired,
                  default=defaultDest,
                  dest='destFolder',
                  help='The destination folder to place the linked .bat file.\n' +
                       'Overrides any defaults set using the --save flag.\n\n',
                  metavar='DEST')

parser.add_argument('-n', '--name',
                  type=str,
                  dest='filename',
                  help='The name of the batch file, excluding the extension.\n' +
                        'Defaults to the name of the target file.\n\n',
                  metavar='NAME')

parser.add_argument('-i', '--interpreter',
                    nargs='?',
                    const=True,
                    default=False,
                    dest='interpreter',
                    help='An interpreter to run the target executable with, if your\n' +
                         'OS won\'t decide on its own. Accepts an absolute path or\n' +
                         'the name of an executable already in your PATH.\n\n')

parser.add_argument('-s', '--save',
                  type=str,
                  nargs='?',
                  const='id',
                  choices=['i', 'd', 'id', 'di', 'interpreter', 'destination'],
                  dest='save',
                  help='Saves the destination folder and chosen interpreter as default.\n' +
                       'When passing an argument, "i" or "interpreter" will save just the\n' +
                       'the interpreter (for the current filetype only), while "d" or\n' +
                       '"destination" will save just the destination.\n\n')

args = parser.parse_args()

# Extract paths
targetPath   = os.path.abspath(args.targetPath)
targetFolder = os.path.dirname(targetPath)
destFolder   = os.path.abspath(args.destFolder)

# Construct pathify destination
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

    # Build prompt
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

    # Change path variables to match new target
    (filename, filetype) = os.path.splitext(result)
    targetPath = os.path.join(targetFolder, filename + filetype)

if not os.path.exists(targetPath):
    sys.exit('ERROR: The target executable could not be found at the given location.')
if not os.path.isfile(targetPath):
    sys.exit('ERROR: The target path does not point to a file.')
if not os.path.exists(destFolder):
    sys.exit('ERROR: The destination folder could not be found.')
if not os.path.isdir(destFolder):
    sys.exit('ERROR: The destination os.path.does not point to a directory.')

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

if interpreter == None:
    sys.exit('ERROR: Flag -i was passed, but no default interpreter exists for filetype "' + filetype + '".')
if interpreter and utils.which(interpreter) == None:
    sys.exit('ERROR: Interpreter "' + interpreter + '" could not be found.')

# Parse save options
if args.save:
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
        config.set('DEFAULT', 'DestinationFolder', args.destFolder)

    if saveOpts['interpreter'] or saveOpts['destination']:
        config.write(open('config.ini', 'w'))

# Read in template file and fill target path and interpreter
template = open(templatePath, 'r').read()
template = template.replace('<DIRECTORY>', targetPath)
template = template.replace('<INTERPRETER> ', interpreter + (' ' if interpreter else ''))

# Write resulting file to the destination folder
writeDestination = True
if os.path.isfile(destPath):
    message = "File '" + os.path.basename(destPath) + "' already exists at '" + destFolder + "'. Overwrite? [y/n]"

    choices = {
        ('y', 'yes'): True,
        ('n', 'no'): False
    }

    writeDestination = utils.prompt(message, choices, {'case_insensitive': True})

if writeDestination:
    destFile = open(destPath, 'w')
    destFile.write(template)
    destFile.close()

# Output results
print('=========================================\n')

if writeDestination:
    print('  Pathification success!')
else:
    print('  Pathification cancelled.')

print('    TARGET:      ' + targetPath)
print('    DESTINATION: ' + destPath)
print('\n=========================================')
