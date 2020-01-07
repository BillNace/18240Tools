#!/usr/bin/python
# handin240.py
#
# Main handin script for students to use to hand in their homework files. Needs
# a .cfg file to know how to handle each file (see the usage in README.md for
# details).
#
# Usage:
#   - cd into the directory with all of the necessary files
#   - Run script with the homework number as the argument:
#       ./handin240 hw1
#   - If the student wishes to submit an incomplete homework (i.e. with certain
#     files missing or unable to compile) they may run the script with the -f flag
#
# Bill Nace <wnace@cmu.edu>         - Reportlab PDF generation
# Edric Kusuma <ekusuma@cmu.edu>    - Student file handin

import ConfigParser
import os
import sys
import shutil
import tempfile
import argparse
import subprocess
import json
import glob

import reportlab

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
import reportlab.rl_config

from contextlib import contextmanager

###################### Some cool output formatting stuff #######################
class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[33m"    # Darker yellow
    #WARNING = "\033[93m"   # Yellow
    #WARNING = "\033[95m"   # Magenta
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

################################################################################

# Return values
###############
HANDIN_YES      = 0
HANDIN_NO       = 1

# Error codes
#############
ERR_CONFIG      = 100
ERR_NOCONFIG    = 101
ERR_BADCONFIG   = 102
ERR_OP          = 200
ERR_NOEXIST     = 201
ERR_NOCOMPILE   = 202
ERR_FAILTEST    = 203
ERR_HANDIN_DIR  = 210
ERR_HANDIN_PERM = 211
ERR_UNKNOWN     = 255

# Initialize config file
########################
conf = ConfigParser.ConfigParser()
scriptPath = os.path.dirname(os.path.realpath(__file__))
conf.read(scriptPath + '/config.ini')

HANDIN_DIR  = conf.get('HANDIN', 'HANDIN_DIR')
CFG_DIR     = conf.get('HANDIN', 'CFG_DIR')
FONT_DIR    = conf.get('PDF', 'FONT_DIR')

# Script errors defined as Exceptions
#####################################
class Handin240Error(Exception):
    def __init__(self, message):
        errMsg = self.getError(message)
        super(Exception, self).__init__(errMsg)
        self.errno = ERR_UNKNOWN

    def getError(self, msg):
        className = self.__class__.__name__
        return "{}{}{}: {}".format(bcolors.FAIL, className, bcolors.ENDC, msg)

class FileError(Handin240Error):
    def __init__(self, files):
        if (isinstance(files, list)):
            fileStr = ", ".join(files)
        else:
            fileStr = files
        msg = "{}: files do not exist".format(fileStr)
        errMsg = self.getError(msg)
        super(Handin240Error, self).__init__(errMsg)
        self.errno = ERR_NOEXIST

class NoConfigError(Handin240Error):
    def __init__(self, hwNum):
        msg = "no config for {} found. ".format(hwNum)
        msg += "Are you sure the HW number is correct?"
        errMsg = self.getError(msg)
        super(Handin240Error, self).__init__(errMsg)
        self.errno = ERR_NOCONFIG

class ParseConfigError(Handin240Error):
    pass

class HandinDirError(Handin240Error):
    def __init__(self):
        msg = "your handin directory was not found. Are you sure "
        msg += "you are enrolled? Please contact course staff if the "
        msg += "problem persists."
        errMsg = self.getError(msg)
        super(Handin240Error, self).__init__(errMsg)
        self.errno = ERR_HANDIN_DIR

class HandinPermError(Handin240Error):
    def __init__(self):
        msg = "access to handin directory denied. Are you "
        msg += "trying to submit past the deadline? If not, please "
        msg += "contact course staff."
        errMsg = self.getError(msg)
        super(Handin240Error, self).__init__(errMsg)
        self.errno = ERR_HANDIN_PERM

# A line of 80 *'s, to mark beginning and end of a header
HEADER_LEN = 80
HEADER_LINE = "*" * HEADER_LEN + "\n"

# List of file types that should not be printed by reportlab
NO_PRINT = [
    ".png",
    ".jpg",
    ".jpeg"
]

################################################################################
#                           Code for the handin script                         #
################################################################################

class Operation:
    """Class that holds the necessary information for a problem's operations

    Attributes:
        number (int): Problem number
        existFiles ([str]): List of files to check for existence.
        compileFiles ([str]): List of files to compile.
        testFiles ([str]): List of TA testbenches to run against. (WIP)
        specificModules ([str]): Name of modules to compile for.
        hasErrors (bool): True if there is an error with the problem, False
            otherwise.
        err (str): Output of error.

    """
    def __init__(self):
        self.number = None
        self.existFiles = None
        self.compileFiles = None
        self.testFiles = None
        self.specificModules = None
        self.hasErrors = False
        self.err = ""
        self.useWildcard = False

    def checkWildcard(self):
        """Checks the list of files for wildcard specifiers, then adds files
        that satisfy the wildcard(s) to the list.

        Args:
            Nothing.

        Returns:
            Nothing.

        """
        tempExistFiles = set()
        tempCompileFiles = set()

        if (self.existFiles != None):
            for f in self.existFiles:
                if ("*" in f):
                # Add all the wildcard files
                    self.useWildcard = True
                    allFiles = set(glob.glob(f))
                    tempExistFiles = tempExistFiles.union(allFiles)
                else:
                    tempExistFiles.add(f)
            # Convert to a list, alphabetical order
            self.existFiles = sorted(list(tempExistFiles))
        if (self.compileFiles != None):
            for f in self.compileFiles:
                if ("*" in f):
                    allFiles = set(glob.glob(f))
                    tempCompileFiles = tempCompileFiles.union(allFiles)
                else:
                    tempCompileFiles.add(f)
            self.compileFiles = sorted(list(tempCompileFiles))

    def parseProblem(self, p):
        """Reads the config file (as a dict) and sets the appropriate
        attributes.

        Args:
            p (dict): Dict of the config file (see readme for keys).

        Returns:
            Nothing.

        """
        if (p["number"] != None):
            self.number = p["number"]
        if (p["files"] != None):
            self.existFiles = p["files"]
        if (p["compileFiles"] != None):
            self.compileFiles = p["compileFiles"]
        if (p["testFiles"] != None):
            self.testFiles = p["testFiles"]
        if (p["specificModules"] != None):
            self.specificModules = p["specificModules"]
        self.checkWildcard()

    def getOpError(self, mainFile, errType):
        """Create a formatted error message depending on what was wrong with the
        file.

        Args:
            mainFile (str): Name of a bad file(s).
            errType (int): Error type to classify problem with file.

        Returns:
            (str): Formatted string to display as an error.

        """
        if (errType == ERR_NOEXIST):
            errMessage = "file does not exist"
        elif (errType == ERR_NOCOMPILE):
            errMessage = "failed to compile"
        elif (errType == ERR_FAILTEST):
            errMessage = "failed TA testbench"
        else:
            errMessage = "unspecified error"
        return mainFile + ": " + bcolors.FAIL + errMessage + bcolors.ENDC

    def checkExistence(self):
        """Checks if every file in a file list exists within the current
        directory. Also lists what files do not exist, if any.

        Args:
            Nothing.

        Returns:
            Nothing.

        """
        if (self.useWildcard):
            print("Files that will be handed in:")
        for f in self.existFiles:
            if (not os.path.exists("./" + f)):
                self.hasErrors = True
                error = self.getOpError(f, ERR_NOEXIST) + "\n"
                print(error.strip())
                self.err += error
            else:
                if (self.useWildcard):
                    print("\t{}".format(f))
                else:
                    print(f + ": file exists, good")
        if (self.useWildcard):
            print("If you do not wish to hand in these files, please move " +
                    "them away from your current directory")

    def removeOldDir(self, fileList, oldDir):
        return ", ".join(fileList).replace("{}/".format(oldDir), "")

    def compilationErrHandler(self, fileList, oldDir, err):
        self.hasErrors = True
        files = self.removeOldDir(fileList, oldDir)
        error = self.getOpError(files, ERR_NOCOMPILE) + "\n"
        print(error.strip())
        self.err += error
        self.err += err.output + "\n"

    def checkCompilation(self):
        """Tries to compile files from a list using VCS (or vLogan+VCS), and
        checks to see if any compilation errors arise.

        Utilizes a temporary directory called `temp240handin`. As of now, this
        function will actually overwrite that directory if it already exists, so
        hope that the user doesn't have a folder with that name. Will remove
        directory on finish.

        If there is an error, it will also print the compiler message to stdout.

        Args:
            Nothing.

        Returns:
            Nothing.

        """
        # Preserve old directory to return to
        oldDir = os.getcwd()
        # Actual files are located in a different directory, so:
        fileList = []
        for fileName in self.compileFiles:
            fileList.append("{}/{}".format(oldDir, fileName))
        # Use tempfile's temporary directory creation. We must delete after done
        tempDir = tempfile.mkdtemp()
        os.chdir(tempDir)

        try:
            if (self.specificModules != None):
                # Command to run vlogan with files
                vloganCmd = ["vlogan", "-q", "-sverilog", "-nc"] + fileList
                try:
                    out = subprocess.check_output(vloganCmd, stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError, e:
                    self.compilationErrHandler(fileList, oldDir, e)
                    return
                for module in self.specificModules:
                    vcsCmd = ["vcs", "-q", "-sverilog", "-nc", module]
                    try:
                        out = subprocess.check_output(vcsCmd, stderr=subprocess.STDOUT)
                    except subprocess.CalledProcessError, e:
                        self.compilationErrHandler(fileList, oldDir, e)
            else:
                vcsCmd = ["vcs", "-q", "-sverilog", "-nc"] + fileList
                try:
                    out = subprocess.check_output(vcsCmd, stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError, e:
                    self.compilationErrHandler(fileList, oldDir, e)
            if (not self.hasErrors):
                files = self.removeOldDir(fileList, oldDir)
                print(files + ": file(s) compile, good")
            return
        except (KeyboardInterrupt):
            raise
        finally:
            # Cleanup
            os.chdir(oldDir)
            shutil.rmtree(tempDir)

    # TODO: checkTATB()

    def do(self):
        """Performs an operation based on the op's attributes.

        Args:
            Nothing.

        Returns:
            (str): The error message.

        """
        if (self.existFiles != None):
            self.checkExistence()
            if (self.hasErrors):
                return self.err + "\n"
        if ((not SKIP_COMP) and (self.compileFiles != None)):
            self.checkCompilation()
            if (self.hasErrors):
                return self.err + "\n"
        return ""

def error(message, fatal=False):
    """Generic error handler.

    If fatal is true, then the error will cause the program to terminate.
        Note that if cleanup is necessary in the case of an error (i.e. deleting
        temporary directories), then fatal should be set to false.

    Args:
        message (string): A message that describes the error.
        fatal (bool): Whether or not the message is fatal (and therefore will
            exit rather than return).

    Returns:
        (int): A non-zero exit code, to signify an error.

    """
    print(bcolors.FAIL + "ERROR: " + bcolors.ENDC + message)
    if (fatal):
        exit(255)
    else:
        return 255

def warning(message):
    """Generic warning handler.

    Args:
        message (string): A message that describes the warning.

    Returns:
        Nothing

    """
    print(bcolors.WARNING + "WARNING: " +bcolors.ENDC + message)

def writeHeaderLine(header, filled=False):
    """Used to write a line in the header for the errors.log file.

    Args:
        header (string): Text to write in one line of the header.

    Returns:
        (string): Formatted header line string.

    """
    maxLen = HEADER_LEN - 2    # Beginning and ending "*"
    header = " " + header + " "
    remaining = maxLen - len(header)
    firstHalf = remaining // 2
    secondHalf = remaining - firstHalf
    if (filled):
        filler = "*"
    else:
        filler = " "
    headerLine = "*" + (filler * firstHalf) + header + (filler * secondHalf) + \
                 "*" + "\n"
    return headerLine

def getArgs():
    """Uses argparse to get script options and args from command line.
    Raises an error (and exits) if no arg for hwNum is given.

    Args:
        Nothing

    Returns:
        (obj): An argparse object whose attributes correspond to the options
            defined via add_option().

    """
    usage = "%(prog)s [-f] hwNum"
    parser = argparse.ArgumentParser(usage=usage)
    parser.add_argument("hwNum", help="number of homework to submit")
    parser.add_argument("-f", "--force", action="store_true", dest="force",
                      help="force handin even with bad files")
    parser.add_argument("-s", "--skip", action="store_true",
                      help="hand in files without compiling")
    parser.add_argument("-n", "--dryrun", action="store_true", dest="dryrun",
                      help="run script without handing in")
    return parser.parse_args()

def parseConfig(configPath):
    """Parses the config JSON file. See README for how these config files must
    be formatted/defined as.

    Raises a fatal error if the path is invalid.

    Args:
        configPath (str): A path leading to the config JSON file. Must be a
            .json file.

    Returns:
        On success:
            (dict): A dictionary that has the parsed JSON mapped onto it. See
                the json module for details on how this is defined.
        On error:
            (None)

    """
    if (not os.path.exists(configPath)):
        raise NoConfigError(HW_NUM)
    configFile = open(configPath, "r")
    try:
        return json.load(configFile)
    except Exception, e:
        msg = "Error parsing config file:\n{}\n\n".format(e)
        msg += "Please contact course staff."
        raise ParseConfigError(msg)
    finally:
        configFile.close()

def createErrLog(contents, path="."):
    """Writes an errors.log file with the formatting characters removed.

    Args:
        contents (str): The stuff to write to the log file.
        path (str): Path to write errors.log (by default CWD).

    Returns:
        Nothing.

    """
    fd = open(path + "/errors.log", "w")

    # Remove formatting characters
    contents = contents.replace(bcolors.HEADER, "")
    contents = contents.replace(bcolors.OKBLUE, "")
    contents = contents.replace(bcolors.OKGREEN, "")
    contents = contents.replace(bcolors.WARNING, "")
    contents = contents.replace(bcolors.FAIL, "")
    contents = contents.replace(bcolors.ENDC, "")
    contents = contents.replace(bcolors.BOLD, "")
    contents = contents.replace(bcolors.UNDERLINE, "")

    fd.write(contents)
    fd.close()

def getOutputHeader(studentID):
    """Writes a formatted header that details hwNum and Andrew ID.

    Args:
        studentID (str): Andrew ID of the student.

    Returns:
        (str): Populated header.

    """
    outputHeader = HEADER_LINE
    outputHeader += writeHeaderLine("18240: " + HW_NUM)
    outputHeader += writeHeaderLine("Error log for: " + studentID)
    outputHeader += HEADER_LINE
    return outputHeader

def checkFs(studentID, studentDir):
    """Checks AFS permissions for a student.

    Args:
        studentID (str): Andrew ID of the student.
        studentDir (str): Path to the folder to check permissions for.

    Returns:
        (bool): True if student has write permissions, False otherwise (and if
            student directory does not exist).

    """
    fsCmd = ["fs", "la", studentDir]
    perms = subprocess.check_output(fsCmd).split()
    try:
        idIndex = perms.index(studentID)
        selfPerms = perms[idIndex:]
    except ValueError:
        error("unable to figure out student permissions for handin dir. " +
              "Please contact course staff if the problem persists.")
        return False

    # Has write permissions
    return "rlidwk" in selfPerms[1]

def doHandin(studentID, filesToSubmit):
    """Perform the handin tasks. Prints relevant errors on failures.

    Args:
        studentID (str): Student's Andrew ID.
        filesToSubmit (set): List of all files to be copied to the handin dir.

    Returns:
        (bool): True on success, False on failure.

    """
    if (DRY):
        return

    studentDir = HANDIN_DIR + "/" + HW_NUM + "/" + studentID
    # Check if student exists in handin directory
    if (not os.path.exists(studentDir)):
        raise HandinDirError()
    goodPerms = checkFs(studentID, studentDir)
    if (not goodPerms):
        raise HandinPermError()

    for fileName in filesToSubmit:
        path = "./" + fileName
        # Since these files passed the check, they should exist, but just in case
        if (not os.path.exists(path)):
            continue
        shutil.copy(path, studentDir)

def printHandinComplete():
    formatStr = "\nCode printout created as {}_code.pdf. Please check "
    formatStr += "that there are no errors in the PDF."
    print(formatStr.format(HW_NUM))
    print(bcolors.WARNING + "Please don't forget to submit this PDF to Gradescope!"
            + bcolors.ENDC)
    print(bcolors.WARNING + "Also don't forget your written homework!"
            + bcolors.ENDC)


################################################################################
#                           Code for the PDF script                            #
################################################################################

#Open my file, still using the "with" context manager goodness, but
# able to detect if the file isn't found (or other errors)
# See PEP 343 for more background
@contextmanager
def opened_with_error(filename, mode='r'):
    try:
        f = open(filename, mode)
    except IOError as err:
        yield None, err
    else:
        try:
            yield f, None
        finally:
            f.close

class HW_Code_Maker:
    """ Make the HWX_code.pdf file for turnin on Gradescope.

    This class encapsulates the functionality to make the HWX_code.pdf
    file.  Such a file is a single PDF with each problem's file(s)
    pretty-printed.  Many problems do not require code, and so nothing
    will be included in this PDF file for those problems.  Some problems
    have a single file and a few have multiple files.

    The resulting PDF will have pages for each file, in order of the
    problem.

    To use, initialize the object with a homework dictionary describing
    the problems in that homework assignment.  Then, call the make_code
    method.
    """

    LINE_SPACING = 10  # points
    TOP_MARGIN   = .5 * inch # points
    LEFT_MARGIN  = .5 * inch # points
    BOTTOM_MARGIN = .5 * inch # points
    BOTTOM_OF_PAGE = 792 - BOTTOM_MARGIN

    def __init__(self, **kwargs):
        """ Initialize with a dictionary describing the HW problems.

        Keyword Arguments: (both are required)
        number : a string used as the homework number.  Typically 0-A
        problems : an ordered list of problem description dictionaries.
                   Exact format is defined in method print_file().
        """
        self.hw_number = kwargs['number']
        self.problems  = kwargs['problems']
        self.student   = kwargs['student']
        self.line_number = 1
        self.init_xy()
        self.canvas = None

    def init_xy(self):
        """ Set the x and y attributes to be the top of the page. """
        self.x = HW_Code_Maker.LEFT_MARGIN
        self.y = HW_Code_Maker.TOP_MARGIN

    def make_code(self):
        """ Make the PDF file with all homework code files printed. """
        filename = '{}_code.pdf'.format(self.hw_number)
        self.canvas = canvas.Canvas(filename,
                                    bottomup=0,
                                    pagesize=reportlab.lib.pagesizes.letter)
        # Need to add to the searchpath, so we can use a font that we specify
        reportlab.rl_config.TTFSearchPath.append(FONT_DIR)
        sFont = TTFont('SourceCodePro', 'SourceCodePro-Regular.ttf')
        pdfmetrics.registerFont(sFont)
        self.canvas.setFont('SourceCodePro', 10)

        for problem in self.problems:
            if problem['files']:
                for filename in problem['files']:
                    self.page_number = 1
                    self.print_file(filename, problem)
        self.canvas.save()

    def draw_text_object(self, a_string, color_style=None):
        """ Draw a string onto the PDF page at the current position.

        Arguments:
        a_string : which will be printed
        color_style : one of 'None', 'Header', 'Warning'
                      Indicates the string should be black, green or red.

        Returns: Nothing

        Note: The y attribute is updated such that the next string to be
              printed will be on a following line.
        """
        text_object = self.canvas.beginText()
        text_object.setTextOrigin(self.x, self.y)
        text_object.setFont('SourceCodePro', 10)
        if color_style == 'Header':
            text_object.setFillColor(colors.green)
        elif color_style == 'Warning':
            text_object.setFillColor(colors.red)
        else:
            text_object.setFillColor(colors.dimgrey)
        text_object.textLine(text=a_string)
        self.canvas.drawText(text_object)
        self.y += HW_Code_Maker.LINE_SPACING

    def draw_header(self, a_filename, prob_dict):
        """ Draw the header at the top of each page.

        The header is one or two lines at the top of each page in the PDF.
        Printed in Green, the header contains information about the problem,
        point values, drill status and filename.
        If the file has taken more than one page, the following headers
        will include a page number.

        Arguments:
        a_filename : the filename of the file being printed.  Note that this
                     is necessary outside of the prob_dict, as there could
                     be multiple files in the problem and we want to know
                     which is currently printing.
        prob_dict : the dictionary describing the problem.  Full documentation
                    of this dictionary is in the print_file method.

        Returns: Nothing
        """
        self.init_xy()
        prob_number = prob_dict['number']
        prob_drill  = prob_dict['drill']
        prob_points = prob_dict['points']
        if self.page_number == 1:
            if (prob_number < 0):   # To be used for lab code
                to_print = 'Lab Code [{} points]'.format(prob_points)
            else:
                to_print = 'Problem {}: [{} points]'.format(prob_number, prob_points)
            if prob_drill:
                to_print = to_print + ' Drill problem'
            self.draw_text_object(to_print, 'Header')
            to_print = 'Filename: {}'.format(a_filename)
            self.draw_text_object(to_print, 'Header')
            # Removed line to preserve anonymity for grading
            # Uncomment if you want to print out student ID as well
            #to_print = '{}'.format(self.student)
            #self.draw_text_object(to_print, 'Header')
        else:
            self.canvas.showPage()
            filename_length = len(a_filename)
            middle_length = 84 - 12 - filename_length - 1
            format_string = 'Filename: {{}} {{:>{}}} {{}}'.format(middle_length)
            to_print = format_string.format(a_filename, 'Page #:', self.page_number)
            self.draw_text_object(to_print, 'Header')
        self.y += HW_Code_Maker.LINE_SPACING # include a blank line
        self.page_number += 1


    def print_file(self, a_filename, prob_dict):
        """ Print a single file into the PDF on one or more pages.

        Each file is 'pretty-printed' in a fixed-width font, with line numbers
        added at the left side.  Note that the line numbers are assumed to
        never be greater than two digits.

        As each line is printed, it is checked for two errors (currently).
        If the line has one or more errors, then it will be printed in Red:
        1) Are there any tab characters on the line.  If so, the tabs are
           replaced by double spaces and an error message is printed after
           the line.
        2) Is the line (with tabs replaced) longer than 80 characters?  If
           so, the first 77 characters of the line are printed, followed
           by three periods ('...').  An error message is then printed which
           specifies how many characters are in the full line.
        Note: a single line could have both errors.

        If the file does not exist, then a red error message is printed
        which states so.

        Arguments:
        a_filename : the filename of the file being printed.  Note that this
                     is necessary outside of the prob_dict, as there could
                     be multiple files in the problem and we want to know
                     which is currently printing.
        prob_dict : a dictionary describing the current homework problem.

        Returns : Nothing

        The dictionary contains the following required keys:
        number : A string with the number of the homework assignment.
        drill : A boolean.  True if this problem is a drill problem.
                            False otherwise.
        points : An integer specifying the number of points for the problem.
        files : A list of filenames required for the problem.  Each element
                in the list is a string.  The elements should be ordered as
                the files should be printed.
                If the problem does not require any files, then this value
                should be a None (i.e. a NoneType)
        """
        self.line_number = 1
        self.draw_header(a_filename, prob_dict)

        with opened_with_error(a_filename) as (f_in, err):
            if err:
                line = 'File {} was not found'.format(a_filename)
                self.draw_text_object(line, color_style='Warning')
            else:
                for line in f_in:
                    if self.y > HW_Code_Maker.BOTTOM_OF_PAGE:
                        self.draw_header(a_filename, prob_dict)
                    contains_tabs = False
                    color_style = 'None'
                    if '\t' in line:
                        contains_tabs = True
                        line = line.replace('\t', '  ')
                        color_style = 'Warning'
                    line = line.rstrip()
                    line_length = len(line)
                    if line_length > 80:
                        to_print = '{:3d} {}...'.format(self.line_number, line[:77]) #truncates to 80 characters.  Ironic comment
                        self.draw_text_object(to_print, color_style='Warning')
                        to_print = 'Line length of {} (max is 80)'.format(line_length)
                        self.draw_text_object(to_print, color_style='Warning')
                    else:
                        to_print = '{:3d} {}'.format(self.line_number, line)
                        self.draw_text_object(to_print, color_style)

                    if contains_tabs:
                        self.draw_text_object('Line contains tabs' +
                               ' (each tab replaced by 2 spaces in this print)',
                               color_style)
                    self.line_number += 1
        self.canvas.showPage()

def makePDF(student, problemDictList):
    cfgPath = CFG_DIR + "/" + HW_NUM + "_cfg.json"
    # TODO: make this more graceful
    for prob in problemDictList:
        tempFiles = set()
        if (prob["files"] != None):
            for f in prob["files"]:
                if ("*" in f):
                    toSkip = False
                    for bad in NO_PRINT:
                        if (bad in f):
                            toSkip = True
                    if (toSkip):
                        continue
                    allFiles = set(glob.glob(f))
                    tempFiles = tempFiles.union(allFiles)
                else:
                    tempFiles.add(f)
        prob["files"] = sorted(list(tempFiles))

    hw_dict = {'number' : HW_NUM, 'problems' : problemDictList,
               'student' : student}

    maker = HW_Code_Maker(**hw_dict)
    maker.make_code()

def makeOpArray(config):
    """Create an array of Operation objects from a config dict.

    Args:
        config (dict): Dict that represents the assignment's config

    Returns:
        ([Operation]): Array of problem ops.

    """
    opArray = []
    # Sort problem config array by problem number
    config = sorted(config, key=lambda p: p["number"])
    for problem in config:
        op = Operation()
        op.parseProblem(problem)
        opArray.append(op)
    return opArray

def doOpArray(opArray):
    resultString = ""
    hasErrors = False
    filesToSubmit = set()

    for op in opArray:
        if (op.existFiles != None):
            filesToSubmit = filesToSubmit.union(set(op.existFiles))
        if (op.compileFiles != None):
            filesToSubmit = filesToSubmit.union(set(op.compileFiles))
        errString = op.do()
        if (op.hasErrors):
            hasErrors = True
            resultString += writeHeaderLine("Problem {}".format(op.number), True)
            resultString += errString
    return (filesToSubmit, hasErrors, resultString)

def searchCfg(fileName):
    """Case-insensitive search for a target config file in CFG_DIR.

    Args:
        fileName (str): Name of the config file to search for.

    Returns:
        (str): Path to the config file.

    """
    fileList = os.listdir(CFG_DIR)
    for f in fileList:
        if (f.lower() == fileName.lower()):
            return "{}/{}".format(CFG_DIR, f)
    raise NoConfigError(HW_NUM)

def handinPrecheck(hasErrors, personalOutput):
    if (not hasErrors):
        return True

    attemptHandin = True
    warning = bcolors.WARNING + "WARNING: " + bcolors.ENDC
    print("\n" + warning + "errors detected! See errors.log for details.\n")
    createErrLog(personalOutput)
    if (not FORCED):
        attemptHandin = False
        print("If you wish to submit an incomplete homework, then run the " +
        "handin script again with the '-f' flag.")
    else:
        print(warning + "you are attempting to submit homework with errors! " +
              "You will NOT receive any credit for files with errors.\n")
        formatStr = "If this is intentional on your part, type '{}' and press Enter: "
        agreement = raw_input(formatStr.format(HW_NUM))
        if (agreement != HW_NUM):
            attemptHandin = False
    return attemptHandin

def main():
    args = getArgs()

    # Save relevant fields
    global FORCED
    FORCED = args.force
    global SKIP_COMP
    SKIP_COMP = args.skip
    global HW_NUM
    HW_NUM = args.hwNum.lower()     # Make case insensitive
    global DRY
    DRY = args.dryrun

    # Initialize variables
    selfID = os.getlogin().lower()  # Get student's Andrew ID

    try:
        # Parse config file and do relevant operations
        cfgPath = searchCfg("{}_cfg.json".format(HW_NUM))
        # Take the proper (case-sensitive) HW_NUM
        HW_NUM = cfgPath[cfgPath.rindex("/")+1:cfgPath.index("_cfg.json")]
        config = parseConfig(CFG_DIR + "/" + HW_NUM + "_cfg.json")
        opArray = makeOpArray(config)
        (filesToSubmit, hasAnyErrors, errString) = doOpArray(opArray)
        personalOutput = getOutputHeader(selfID)
        personalOutput += errString
    except (KeyboardInterrupt, SystemExit):
        raise
    except (Handin240Error) as e:
        print(e)
        return e.errno
    except:
        print("Encountered unknown error.")
        return ERR_UNKNOWN

    # Result strings WITH COLORS \o/
    handinCreated = bcolors.OKGREEN + "Handin complete." + bcolors.ENDC
    handinNotCreated = bcolors.FAIL + "Handin not complete." + bcolors.ENDC

    if (SKIP_COMP):
        skip_warning = bcolors.WARNING + "\nWARNING: " + bcolors.ENDC
        skip_warning += "you are choosing to skip compilation checks. Note that "
        skip_warning += "code that doesn't compile WILL get ZERO credit."
        print(skip_warning)
    # Check if handin had any errors
    attemptHandin = handinPrecheck(hasAnyErrors, personalOutput)

    if (attemptHandin):
        try:
            doHandin(selfID, filesToSubmit)
            if (DRY):
                print("\n'-n' flag specified. Handin was not done")
                print(handinNotCreated)
                status = HANDIN_NO
            else:
                print("\n" + handinCreated)
                status = HANDIN_YES
            # Create output PDF
            makePDF(selfID, config)
            printHandinComplete()
            return status
        except (KeyboardInterrupt, SystemExit):
            raise
        except (Handin240Error) as e:
            print(e)
            print("\n" + handinNotCreated)
            return HANDIN_NO
        except:
            print("Encountered unknown error.")
            return ERR_UNKNOWN
    else:
        print("\n" + handinNotCreated)
        return HANDIN_NO

sys.exit(main())
