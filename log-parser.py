'''
    Author: Ricky Bhatia
    
    Version History:
    0.7 [12/10/2016]
        moved filters to new class and restructured code
        modified FullPath to be output as a hyperlink
        added support to report all files via a config flag report_all
        fixed issue with report_all (12/14/2016)
        added support for size filtering (12/15/2016)
        
    0.6 [12/09/2016]
        Updates to filter files based on CTime
        Pass the config file from command line argument
        
    0.5 [12/08/2016]
        re-write to make fields and patterns configurable
        
    0.4
        Changed first column to basename and last column as full path
    0.3
        Timestamp the output file name
        Case insensitive pattern matching
        Added field for file creation timestamp
        Ability to log to file as well as STDOUT
    0.2
        Fixed issue with dictionary copy()
'''

import glob
import re 
import csv
import time
import sys
import os.path
import ConfigParser

__version__ = 0.7

             
class Logger(object):
    def __init__(self, log_fname):
        self.terminal = sys.stdout
        self.log = open(log_fname, "w")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        pass    
        
class filters(object):
    def __init__(self, config):
        self.apply_filter = config.getboolean('DEFAULTS','apply_filter')
        self.lstFilters = config.get('filters','type').split(',')
        self.timeFormat = config.get('filters','format')
        self.dictFilters  = {}
        for key in ['ctime_after','ctime_before','mtime_after','mtime_before']:
            if config.get('filters',key):
                self.dictFilters[key] = time.mktime(time.strptime(config.get('filters',key), self.timeFormat))
            else:
                self.dictFilters[key] = config.get('filters',key)
        for key in ['size_gt','size_lt']:
            if config.get('filters',key):
                self.dictFilters[key] = long(config.get('filters',key))
            else:
                self.dictFilters[key] = config.get('filters',key)
                
    def applyFilter(self, filename):
        valid = True
        if self.apply_filter:
            if 'ctime' in self.lstFilters:
                if self.dictFilters['ctime_after']:
                    valid = valid and (os.path.getctime(filename) > self.dictFilters['ctime_after'])
                if self.dictFilters['ctime_before']:
                    valid = valid and (os.path.getctime(filename) < self.dictFilters['ctime_before'])
            if 'mtime' in self.lstFilters:
                if self.dictFilters['mtime_after']:
                    valid = valid and (os.path.getmtime(filename) > self.dictFilters['mtime_after'])
                if self.dictFilters['mtime_before']:
                    valid = valid and (os.path.getmtime(filename) < self.dictFilters['mtime_before'])
            if 'size' in self.lstFilters:
                if self.dictFilters['size_gt']:
                    valid = valid and (os.path.getsize(filename) > self.dictFilters['size_gt'])
                if self.dictFilters['size_lt']:
                    valid = valid and (os.path.getsize(filename) < self.dictFilters['size_lt'])
        return valid
        
class logParser(object):
    def __init__(self, cfg_path):
        self.config = ConfigParser.ConfigParser()
        self.config.read(cfg_path)
        self.starttime = time.strftime("%Y%m%d-%H%M%S")
        self.reportname  = '%s_%s.csv' % (self.config.get('DEFAULTS','report_prefix'), self.starttime)
        self.logfilename = '%s_%s.log' % (self.config.get('DEFAULTS','report_prefix'), self.starttime)
        self.reportAll = self.config.getboolean('DEFAULTS','report_all')
        self.filters = filters(self.config)
        self.filesParsed = 0
        self.filesOutput = 0
        self.filesFound  = 0
        self.startTime = time.time()
        
    def writeHeader(self):
        self.csvfile = open(self.reportname, 'wb')
        self.writer  = csv.DictWriter(self.csvfile, fieldnames=['Filename','CTime'] + self.config.options('pathfields') + self.config.options('fields') + ['Line', 'Key', 'Value', 'FullPath'])
        self.writer.writeheader()
        
    def writeRows(self, rows):
        self.writer.writerows(rows)
        
    def doParse(self):
        print(time.asctime(), "Start Parsing...")
        for filepath in glob.iglob(self.config.get('DEFAULTS','filepattern')):
            #print filepath
            self.filesFound+=1
            if self.filters.applyFilter(filepath):
                print filepath
                self.filesParsed+=1
                output = {}
                rowsout = []
                output['Filename']  = os.path.basename(filepath)
                output['FullPath'] = "=HYPERLINK(\"%s\")" % (filepath)
                output['CTime']   = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getctime(filepath)))
                for field, pattern in self.config.items('pathfields'):
                    output[field] = "|".join(re.findall(pattern,filepath, re.IGNORECASE))
                for i, line in enumerate(open(filepath)):
                    for field, pattern in self.config.items('fields'):
                        for match in re.finditer(pattern, line, re.IGNORECASE):
                            #print "\t", field, ":", match.group(1)
                            output[field] = ":".join(match.groups())
                    for field, pattern in self.config.items('searches'):
                        for match in re.finditer(pattern, line, re.IGNORECASE):
                            output['Line'] = i+1
                            output['Key'] = field
                            output['Value'] = match.group(1)
                            rowsout.append(output.copy())
                            print("\t", field, ":", match.group(1))
                if rowsout:
                    self.filesOutput+=1
                    self.writeRows(rowsout)
                elif self.reportAll:
                    self.filesOutput+=1
                    self.writer.writerow(output)

        print("\nDone creating %s at %s" % (self.reportname, time.asctime()))
        self.__writeSummary()
        
    def __writeSummary(self):
        print("=" * 60)
        print("Total Files Found\t:", self.filesFound)
        print("Total Files Parsed\t:", self.filesParsed)
        print("Total Files Output\t:", self.filesOutput)
        m,s = divmod(time.time() - self.startTime, 60)
        h,m = divmod(m, 60)
        print("Total time taken\t: %02d Hrs %02d Mins %02d Secs" % (h, m, s))
        print("=" * 60)
        
    def closeReport(self):
        self.csvfile.close()

def __checkArgs():
    if len(sys.argv) == 1:
        __printUsage()
        exit()
    if os.path.isfile(sys.argv[1]):
        return
    else:
        print("Path not found -", sys.argv[1])
        __printUsage()
        exit()
        
def __printUsage():
    print("Usage : log-parser.py <path_of_config_file>")
    print("For Eg: log-parser.py appLogs.ini")

if __name__ == '__main__':
    __checkArgs()
    objParser = logParser(cfg_path=sys.argv[1])
    if objParser.config.getboolean('DEFAULTS','create_log'):
        sys.stdout = Logger(objParser.logfilename)
    objParser.writeHeader()
    objParser.doParse()
    objParser.closeReport()
