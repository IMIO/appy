#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# ~license~

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# This module implements "integration" testing. It works by:
# - defining an executable test plan as an ODT file containing tests as tables
#   conforming to conventions as described in appy/utils/tables.py ;
# - executing this plan, or only a sub-part of its tests ;
# - producing a report about success or failure of every test ran.

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
from pathlib import Path
import os, os.path, sys, time

from appy.bin import Program
from appy.xml.diff import Diff
from appy.utils import Traceback
from appy.utils import path as putils
from appy.utils.tables import TablesParser

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class TesterError(Exception): pass
class InternalError(Exception): pass

# TesterError-related constants
WRONG_TEST_PLAN = 'The test plan you specified does not correspond to an ' \
  'existing ODT file.'
_FLAVOUR = 'A flavour represents a test configuration.'
FLAVOURS_NOT_LIST = 'The flavours specified must be a list or tuple of ' \
  'string. ' + _FLAVOUR
FLAVOUR_NOT_STRING = 'Each specified flavour must be a string. ' + _FLAVOUR
WRONG_TEST_FACTORY = 'You must give a test factory that inherits from the ' \
  'abstract "appy.shared.test.TestFactory" class.'
CREATE_TEST_NOT_OVERRIDDEN = 'The appy.shared.test.TestFactory.createTest ' \
  'method must be overridden in your concrete TestFactory.'
MAIN_TABLE_NOT_FOUND = 'No table "TestSuites" found in test plan "%s".'
MAIN_TABLE_MALFORMED = 'The "TestSuites" table must have at least two ' \
  'columns, named "Name" and "Description".'
TEST_SUITE_NOT_FOUND = 'Table "%s.descriptions" and/or "%s.data" were not ' \
  'found.'
TEST_SUITE_MALFORMED = 'Tables "%s.descriptions" and "%s.data" do not have ' \
  'the same length. For each test in "%s.data", You should have one line in ' \
  '"%s.descriptions" describing the test.'
FILE_NOT_FOUND = 'File to compare "%s" was not found.'
WRONG_FLAVOUR = 'Wrong flavour "%s". Flavour must be one of %s.'
TEST_AND_SUITE = 'Specify a single test or test suite but not both.'

# InternalError-related constants
TEST_REPORT_SINGLETON_ERROR = 'You can only use the TestReport constructor ' \
  'once. After that you can access the single TestReport instance via the ' \
  'TestReport.instance static member.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class TestReport:
    '''Collects data about test results for producing a report'''

    # The single TestReport instance to be ever created
    instance = None

    def __init__(self, reportPath, verbose):
        if TestReport.instance is None:
            self.report = open(str(reportPath), 'w')
            self.verbose = verbose
            TestReport.instance = self
        else:
            raise InternalError(TEST_REPORT_SINGLETON_ERROR)

    def say(self, msg, force=False):
        if self.verbose or force:
            print(msg)
        self.report.write(msg)
        self.report.write('\n')

    def close(self): self.report.close()

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Test:
    '''Abstract test class'''
    def __init__(self, testData, testDescription, testFolder,
                 config, flavour, rendererParams):
        self.data = testData
        self.description = testDescription
        self.testFolder = testFolder
        self.tempFolder = None
        self.report = TestReport.instance
        self.errorDump = None
        self.config = config
        self.flavour = flavour
        self.rendererParams = rendererParams

    def compareFiles(self, expected, actual, areXml=False, xmlTagsToIgnore=(),
                     xmlAttrsToIgnore=()):
        '''Compares 2 files. r_ is True if files are different. The differences
        are written in the test report.'''
        for f in expected, actual:
            assert os.path.exists(f), TesterError(FILE_NOT_FOUND % f)
        # Expected result (may be different according to flavour)
        if self.flavour:
            expectedFlavourSpecific = '%s.%s' % (expected, self.flavour)
            if os.path.exists(expectedFlavourSpecific):
                expected = expectedFlavourSpecific
        # Perform the comparison
        differ = Diff(actual, expected, areXml, xmlTagsToIgnore,
                          xmlAttrsToIgnore)
        return not differ.filesAreIdentical(report=self.report)

    def run(self):
        say = self.report.say
        say('-' * 79)
        say('- Test %s.' % self.data['Name'])
        say('- %s\n' % self.description)
        # Prepare test data
        self.tempFolder = self.testFolder / 'temp'
        if self.tempFolder.exists():
            putils.FolderDeleter.delete(self.tempFolder)
        self.tempFolder.mkdir()
        try:
            self.do()
            say('Checking result...')
            testFailed = self.checkResult()
        except:
            testFailed = self.onError()
        self.finalize()
        return testFailed

    def do(self):
        '''Concrete part of the test. Must be overridden.'''

    def checkResult(self):
        '''r_ is False if the test succeeded.'''
        return True

    def onError(self):
        '''What must happen when an exception is raised during test
           execution? Returns True if the test failed.'''
        self.errorDump = Traceback.get()
        self.report.say('Exception occurred:')
        self.report.say(self.errorDump)
        return True

    def finalize(self):
        '''Performs sme cleaning actions after test execution.'''
        pass

    def isExpectedError(self, expectedMessage):
        '''An exception was thrown. So check if the actual error message
           (stored in self.errorDump) corresponds to the p_expectedMessage.'''
        res = True
        for line in expectedMessage:
            if (self.errorDump.find(line) == -1):
                res = False
                self.report.say('"%s" not found among error dump.' % line)
                break
        return res

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class TestFactory:
    @staticmethod
    def createTest(testData, testDescription, testFolder, config, flavour,
                   rendererParams):
        '''This method allows you to create tests that are instances of classes
           that you create. Those classes must be children of
           appy.shared.test.Test. m_createTest must return a Test instance and
           is called every time a test definition is encountered in the test
           plan.'''
        raise TesterError(CREATE_TEST_NOT_OVERRIDDEN)

# Program help - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
HELP_VERBOSE = 'Dumps the whole test report on stdout'
HELP_KEEP_TEMP = 'Keep the temp folder, in order to be able to copy some ' \
  'results and make them expected results when needed.'
HELP_TEST = 'Run only a specified test.'
HELP_TEST_SUITE = 'Run only a specified test suite.'
HELP_RENDERER_PARAMS = 'Specific renderer parameters, of the form ' \
  'name1=val1,name2=v2'
HELP_FLAVOUR = 'Specify the configuration flavour, which may be one of %s.'

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
class Tester(Program):
    def __init__(self, testPlan, flavours, testFactory):
        # Check test plan
        plan = Path(testPlan)
        if not plan.is_file() or not plan.name.endswith('.odt'):
            raise TesterError(WRONG_TEST_PLAN)
        self.testPlan = plan
        self.testFolder = plan.absolute().parent
        # Check flavours
        if (not isinstance(flavours,list)) and (not isinstance(flavours,tuple)):
            raise TesterError(FLAVOURS_NOT_LIST)
        for flavour in flavours:
            if not isinstance(flavour, str):
                raise TesterError(FLAVOUR_NOT_STRING)
        self.flavours = flavours
        self.flavour = None
        # Check test factory
        if not issubclass(testFactory, TestFactory):
            raise TesterError(WRONG_TEST_FACTORY)
        self.testFactory = testFactory
        # Call the base constructor: it will read and check args
        Program.__init__(self)
        # Create the report that will collect info from all executed tests
        self.report = TestReport(self.testFolder / 'Tester.report',
                                 self.verbose)

    def getRendererParams(self, params):
        '''Returns a dict with additional Renderer params'''
        r = {}
        if not params: return r
        for param in params.split(','):
            name, value = param.split('=')
            r[name] = value
        return r

    def defineArguments(self):
        '''Define the allowed arguments for this program'''
        parser = self.parser
        add = parser.add_argument
        if self.flavours:
            add('flavour', help=Make.HELP_FLAVOUR % self.flavours)
        add('-v', '--verbose', action='store_true', help=HELP_VERBOSE)
        add('-k', '--keepTemp', action='store_true', help=HELP_KEEP_TEMP)
        add('-t', '--test', help=HELP_TEST)
        add('-s', '--testSuite', help=HELP_TEST_SUITE)
        add('-r', '--rendererParams', help=HELP_RENDERER_PARAMS)

    def analyseArguments(self):
        '''Check arguments'''
        if self.flavours:
            sflavours = ', '.join(self.flavours)
            if self.flavour not in self.flavours:
                raise TesterError(WRONG_FLAVOUR % (self.flavour, sflavours))
        args = self.args
        self.verbose = args.verbose
        self.keepTemp = args.keepTemp
        self.rendererParams = self.getRendererParams(args.rendererParams)
        # If the user wants to run a single test
        self.singleTest = args.test
        # If the user wants to run a single test suite
        self.singleSuite = args.testSuite
        if self.singleTest and self.singleSuite:
            raise TesterError(TEST_AND_SUITE)

    def runSuite(self, suite):
        self.report.say('*' * 79)
        self.report.say('* Suite %s.' % suite['Name'])
        self.report.say('* %s\n' % suite['Description'])
        i = -1
        for testData in self.tables['%s.data' % suite['Name']]:
            self.nbOfTests += 1
            i += 1
            testName = testData['Name']
            if testName.startswith('_'):
                self.nbOfIgnoredTests += 1
            elif self.singleTest and (testName != self.singleTest):
                self.nbOfIgnoredTests += 1
            else:
                description = self.tables['%s.descriptions' % \
                                          suite['Name']][i]['Description']
                test = self.testFactory.createTest(
                    testData, description, self.testFolder, self.config,
                    self.flavour, self.rendererParams)
                testFailed = test.run()
                if not self.verbose:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                if testFailed:
                    self.report.say('Test failed.\n')
                else:
                    self.report.say('Test successful.\n')
                    self.nbOfSuccesses += 1
    def run(self):
        '''Runs the tests'''
        self.startTime = time.time()
        self.report.say('Parsing ODT file... ')
        self.tables = tables = TablesParser(self.testPlan).run()
        self.config = None
        ext = '.%s' % self.flavour if self.flavour else ''
        configTableName = 'Configuration%s' % ext
        if configTableName in tables:
            self.config = tables[configTableName].asDict()
        self.tempFolder = os.path.join(self.testFolder, 'temp')
        if os.path.exists(self.tempFolder):
            putils.FolderDeleter.delete(self.tempFolder)
        self.nbOfTests = 0
        self.nbOfSuccesses = 0
        self.nbOfIgnoredTests = 0
        if 'TestSuites' not in tables:
            raise TesterError(MAIN_TABLE_NOT_FOUND % str(self.testPlan))
        # Browse test suites
        for suite in tables['TestSuites']:
            if ('Name' not in suite) or ('Description' not in suite):
                raise TesterError(MAIN_TABLE_MALFORMED)
            # Must we ignore this test suite ?
            if suite['Name'].startswith('_'):
                name = suite['Name'][1:]
                tsIgnored = True
            else:
                name = suite['Name']
                tsIgnored = self.singleSuite and (name != self.singleSuite)
            # For every suite, 2 tables must exist: one with test descriptions
            # and the other with test data.
            descrTable = tables.get('%s.descriptions' % name)
            dataTable = tables.get('%s.data' % name)
            if not descrTable or not dataTable:
                raise TesterError(TEST_SUITE_NOT_FOUND % (name, name))
            if len(descrTable) != len(dataTable):
                raise TesterError(TEST_SUITE_MALFORMED % ((name,)*4))
            # The suite can still be ignored if self.singleTest is not among it
            if self.singleTest:
                inSuite = False
                for test in dataTable:
                    testName = test['Name']
                    if testName.startswith('_'): testName = testName[1:]
                    if testName == self.singleTest:
                        inSuite = True
                        break
                if not inSuite: tsIgnored = True
            if tsIgnored:
                nbOfIgnoredTests = len(dataTable)
                self.nbOfIgnoredTests += nbOfIgnoredTests
                self.nbOfTests += nbOfIgnoredTests
            else:
                self.runSuite(suite)
        self.finalize()

    def finalize(self):
        duration = time.time() - self.startTime
        msg = '%d/%d successful test(s) performed in %.2f seconds' % \
              (self.nbOfSuccesses, (self.nbOfTests-self.nbOfIgnoredTests),
               duration)
        if self.nbOfIgnoredTests >0:
            msg += ', but %d ignored test(s) not counted' % \
                   self.nbOfIgnoredTests
        msg += '.'
        self.report.say(msg, force=True)
        self.report.close()
        if not self.keepTemp:
            if os.path.exists(self.tempFolder):
                putils.FolderDeleter.delete(self.tempFolder)
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
