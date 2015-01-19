import argparse
import configparser
import os
import sys

# Get os.path. of important files
templatePath = os.path.join(os.path.dirname(__file__), 'template.bat')
configPath   = os.path.join(os.path.dirname(__file__), 'config.ini')

# Parse defaults
config = configparser.ConfigParser()
config.read(configPath)

# If a default destination is specified, don't require the -d option
defaultDest  = config.get('DEFAULT', 'DestinationFolder', fallback=None)
destRequired = defaultDest == None

# Parse arguments
parser = argparse.ArgumentParser(description='Creates a .bat file that redirects to a target executable. ' +
                                             'Useful for selectively adding programs to the PATH environment variable.',
				 formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('-t', '--target',
		  dest='targetPath',
		  required=True,
		  help='The target executable.\n\n',
		  metavar='TARGET')

parser.add_argument('-d', '--destination',
		  dest='destFolder',
		  required=destRequired,
		  default=defaultDest,
		  help='The destination folder to place the linked .bat file.\n' +
		       'Overrides any defaults set using the --save flag.\n\n',
		  metavar='DEST')

parser.add_argument('-n', '--name',
		  dest='filename',
		  help='The name of the batch file, excluding the extension.\n' +
		        'Defaults to the name of the target file.\n\n',
		  metavar='NAME')

parser.add_argument('-s', '--save',
		  dest='save',
		  action='store_true',
		  help='Saves the destination folder as default.\n\n')

args = parser.parse_args()

# Extract paths
targetPath = os.path.abspath(args.targetPath)
destFolder = os.path.abspath(args.destFolder)

if not os.path.exists(targetPath):
    sys.exit('ERROR: The target executable could not be found at the given location.')
if not os.path.isfile(targetPath):
    sys.exit('ERROR: The target os.path.does not point to a file.')
elif not os.path.exists(destFolder):
    sys.exit('ERROR: The destination folder could not be found.')
elif not os.path.isdir(destFolder):
    sys.exit('ERROR: The destination os.path.does not point to a directory.')

# Set default if --save is passed
if args.save and (args.destFolder != defaultDest):
    config.set('DEFAULT', 'DestinationFolder', args.destFolder)
    config.write(open('config.ini', 'w'))

# Read in template file and insert target path
template = open(templatePath, 'r').read()
template = template.replace('<DIRECTORY>', targetPath)

# Construct path for .bat file
filename = args.filename or os.path.splitext(os.path.basename(targetPath))[0]
destPath = os.path.join(destFolder, filename) + os.path.splitext(templatePath)[1]

# Write resulting file to the destination folder
destFile = open(destPath, 'w')
destFile.write(template)
destFile.close()
