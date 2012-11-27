#!/usr/bin/env python
#  Copyright 2008-2011 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from math import ceil
import os
import random
import shutil
import time
import sys
import sqlite3
from sqlite3 import OperationalError
import copy
from time import strftime
from optparse import OptionParser

ROOT = os.path.dirname(__file__)
lib = os.path.join(ROOT, '..', 'lib')
src = os.path.join(ROOT, '..', 'src')

sys.path.insert(0, lib)
sys.path.insert(0, src)


def _create_test_libraries(path, filecount = 10, keywords=10):
    global db_cursor, verbs, words

    libs = []

    for x in range(filecount):
        lib_main = random.choice(words).strip().capitalize()
        lib_name = "CustomLib%s" % lib_main
        libs.append(lib_name)
        db_cursor.execute("INSERT INTO source (path,type) VALUES ('%s','CUSTOMLIBRARY')" % lib_name)
        libfile = open("%s/%s.py" % (path,lib_name),"w")
        lib_doc = '"""Library documentation:\n'\
                  '\t%s"""' % lib_name
        libfile.write(\
            """
            import os,time

            class %s:
                def __init__(self):
                    %s
            """ % (lib_name, lib_doc))

        directory_looper = """for dirname, dirnames, filenames in os.walk('.'):
            for subdirname in dirnames:
                print os.path.join(dirname, subdirname)
            for filename in filenames:
                print os.path.join(dirname, filename)"""
        sleeper = "time.sleep(1)"

        libfile.write("\t" + random.choice([directory_looper, sleeper]) + "\n")

        temp_verb = copy.copy(verbs)
        counter = 1
        for x in range(keywords):
            if len(temp_verb) > 0:
                verb = temp_verb.pop().capitalize()
            else:
                verb = "KW_%d" % counter
                counter += 1
            kw_name = verb + "_" + lib_main
            db_cursor.execute("INSERT INTO keywords (name,source) VALUES ('%s','%s')" % (kw_name,lib_name))
            kw_doc = '"""Keyword documentation for %s"""' % kw_name
            libfile.write(\
                """
                    def %s(self):
                        %s
                        %s
                """ % (kw_name,kw_doc,random.choice([directory_looper, sleeper, "pass"])))

        libfile.write(\
            """
            myinstance = %s()
            """ % lib_name)
        libfile.close()

    #initfile_lines = open("%s/__init__.txt" % path).readlines()
    index = 0

#    for line in initfile_lines:
#        if "*** Settings ***" in line:
#            index += 1
#            for lib_name in libs:
#                initfile_lines.insert(index, "Library\t%s.py\n" % lib_name)
#                index += 1
#            break
#        index += 1

#fo = open("%s/__init__.txt" % path, "w")
#for line in initfile_lines:
#    fo.write(line)
#fo.close()


def _create_test_suite(path, filecount = 1, testcount = 20, avg_test_depth = 5, test_validity = 1):
    global db_cursor, verbs, words, common_tags

    available_resources = db_cursor.execute(
        "SELECT path FROM source WHERE type = 'RESOURCE' ORDER BY RANDOM()").fetchall()
    for testfile_index in range(filecount):
        libraries_in_use = {}
        resources_in_use = []
        generated_errors = 0
        settings_txt = ""
        test_txt = ""
        keywords_txt = ""
        available_libraries = db_cursor.execute("SELECT path FROM source WHERE type = 'CUSTOMLIBRARY'").fetchall()

        tcfile = open("%s/T%d_CustomTests.txt" % (path, testfile_index+1),"w")
        suite_tag = random.choice(common_tags)
        test_txt += "*** Test Cases ***\n"
        for tc in range(testcount):
            generate_error = False
            if test_validity < 1 and random.random() > (test_validity*1.0):
                generate_error = True
            selected_library = random.choice(available_libraries)[0]
            testlib = selected_library
            if selected_library not in libraries_in_use.values():
                use_with_name = random.choice([True,False])
                if use_with_name:
                    testlib = "Cus%d" % tc
                    libraries_in_use[testlib] = selected_library
                else:
                    libraries_in_use[selected_library] = selected_library
            else:
                for key,val in libraries_in_use.iteritems():
                    if val == selected_library:
                        testlib = key
                        break
            tc_name = "Test %s in %s #%d" % (random.choice(verbs), selected_library.split("CustomLib")[1], tc)
            available_keywords = db_cursor.execute("SELECT * FROM keywords WHERE source IN ('%s','BuiltIn','OperatingSystem','String') ORDER BY RANDOM()"
                                                   % selected_library).fetchall()
            kwlib = random.choice([selected_library, testlib, testlib + "xyz"])
            test_txt += "%s\t[Documentation]\t%s" % (tc_name, "Test %d - %s\\n\\n%s" % (tc,strftime("%d.%m.%Y %H:%M:%S"),random.choice(words).strip()))
            test_tag = random.choice(common_tags)
            if test_tag != suite_tag and random.choice([1,2]) == 1:
                test_txt += "\n\t[Tags]\t%s\n" % test_tag

            for i in range(avg_test_depth+random.choice([-1,0,1])):
                kw1 = available_keywords.pop()
                kw_library = kw1[2]
                for key,val in libraries_in_use.iteritems():
                    if val == kw_library:
                        kw_library = key
                kw_action = kw1[1].replace("_"," ")
                if generate_error:
                    kw_action += "_X"
                    generate_error = False
                    generated_errors += 1
                if kw_library in ('BuiltIn','OperatingSystem','String'):
                    kw_total = kw_action
                else:
                    kw_total = "%s.%s" % (kw_library,kw_action)
                kw_args = kw1[3]
                kw_return = kw1[4]
                argument = None
                return_statement = None
                if kw_args == 1:
                    argument = random.choice(words).strip().lower()
                if kw_return == 1:
                    return_statement = "${ret}="
                test_txt += "\t\t"
                if return_statement:
                    test_txt += return_statement
                test_txt += "\t%s" % kw_total
                if argument:
                    if kw_action == "Count Files In Directory":
                        test_txt += "\t" + os.path.join(os.path.abspath(os.curdir), path)
                    else:
                        test_txt += "\t" + argument
                test_txt += "\n"
                if return_statement:
                    test_txt += "\t\tLog\t${ret}\n"
            if tc == testcount-1 and generated_errors == 0 and test_validity < 1:
                test_txt += "\t\tLogX\t${ret}\n"
            test_txt += "\n"

        settings_txt += "*** Settings ***\n"
        for testlib_key,testlib_value in libraries_in_use.iteritems():
            if testlib_key != testlib_value:
                settings_txt += "Library    %45s.py\tWITH NAME\t%s\n" % (testlib_value, testlib_key)
            else:
                settings_txt += "Library    %45s.py\n" % (testlib_value)
        settings_txt += "Library\tOperatingSystem\n"
        settings_txt += "Library\tString\n"
        settings_txt += "Force Tags\t%s\n" % suite_tag

        for x in range(random.randint(0,2)):
            try:
                selected_resource = available_resources.pop()[0]
                settings_txt += "Resource   %45s\n" % selected_resource
            except IndexError:
                break
        settings_txt += "\n"
        keywords_txt += "*** Keywords ***\n"
        keywords_txt += "My Keyword\n\tNo Operation\n"
        tcfile.write(settings_txt)
        tcfile.write(test_txt)
        tcfile.write(keywords_txt)
        tcfile.close()


def _create_test_resources(path, resources_in_file, resource_count, subdir = ""):
    global db_cursor, verbs, words

    for resfile_index in range(resources_in_file):
        basename = "R%d_Resource.txt" % (resfile_index+1)
        if subdir != "":
            rf_resource_name = subdir + "${/}" + basename
            fullpath = path + os.sep + subdir + os.sep
            if not os.path.exists(fullpath):
                os.makedirs(fullpath)
            resfile_ondisk = open("%s%s" % (fullpath, basename) ,"w")
        else:
            rf_resource_name = basename
            resfile_ondisk = open("%s%s" % (path + os.sep, basename) ,"w")
        content = "*** Settings ***\n"
        #available_keywords = db_cursor.execute("SELECT * FROM keywords ORDER BY RANDOM()").fetchall()
        content += "\n*** Variables ***\n"
        for x in range(resource_count):
            content += "%-25s%10s%d\n" % ("${%s%d}" % (random.choice(words).strip().capitalize(),x),"",
                                          random.randint(1,1000))
        content += "\n*** Keywords ***\n"
        resfile_ondisk.write(content)
        resfile_ondisk.close()
        db_cursor.execute("INSERT INTO source (path,type) VALUES ('%s','RESOURCE')" % rf_resource_name)


def _create_test_project(thetestdir,testlibs_count=5,keyword_count=10,testsuite_count=5,tests_in_suite=10,
                         resource_count=10,resources_in_file=20,avg_test_depth=5,test_validity=1):
    print """Generating test project with following settings
    %d test libraries (option 'l')
    %d keywords per test library (option 'k')
    %d test suites (option 's')
    %d tests per test suite (option 't')
    %d test steps per test case (option 'e')
    %d resource files (option 'f')
    %d resources per resource file (option 'r')""" % (testlibs_count, keyword_count, testsuite_count,
                                                      tests_in_suite, avg_test_depth, resource_count, resources_in_file)

    _create_test_libraries(thetestdir, filecount=testlibs_count, keywords=keyword_count)
    _create_test_resources(thetestdir,subdir="resources", resources_in_file=resource_count,resource_count=resources_in_file)
    _create_test_suite(thetestdir, filecount=testsuite_count, testcount=tests_in_suite, avg_test_depth=avg_test_depth,test_validity=test_validity)


def main(path,testlibs_count=25,keyword_count=10,testsuite_count=30,tests_in_suite=40,resource_count=10,
         resources_in_file=100,avg_test_depth=3,test_validity=1):
    global db_connection, db_cursor, words

    if avg_test_depth < 2:
        avg_test_depth = 2
    elif avg_test_depth > 20:
        avg_test_depth = 20
    if test_validity > 1:
        test_validity = 1
    elif test_validity < 0:
        test_validity = 0

    db_connection=sqlite3.connect(os.path.join(path, "testdata.db"))
    db_cursor=db_connection.cursor()
    try:
        db_cursor.execute('CREATE TABLE IF NOT EXISTS source (id INTEGER PRIMARY KEY, path TEXT, type TEXT)')
        db_cursor.execute('CREATE TABLE IF NOT EXISTS keywords (id INTEGER PRIMARY KEY, name TEXT, source TEXT, arguments INTEGER, returns INTEGER)')
        db_cursor.execute('DELETE FROM source')
        db_cursor.execute('DELETE FROM keywords')
        libs_to_insert = [("BuiltIn","LIBRARY"),("OperatingSystem","LIBRARY"),("String","LIBRARY")]
        db_cursor.executemany('INSERT INTO source (path,type) VALUES (?,?)', libs_to_insert)
        keywords_to_insert = [("Log","BuiltIn",1,0),("No Operation","BuiltIn",0,0),("Get Time","BuiltIn",0,1),
                              ("Count Files In Directory","OperatingSystem",1,1),("Get Environment Variables","OperatingSystem",0,1),
                              ("Get Time","BuiltIn",0,1)]
        db_cursor.executemany('INSERT INTO keywords (name,source,arguments,returns) VALUES (?,?,?,?)', keywords_to_insert)
        db_connection.commit()
    except OperationalError, err:
        print "DB error: ",err

    _create_test_project(path,testlibs_count,keyword_count,testsuite_count,tests_in_suite,resource_count,
        resources_in_file,avg_test_depth,test_validity)
    result = "PASS"
    return result != 'FAIL'


# Global variables
start_time = None
end_time = None

db_connection = None
db_cursor = None

common_tags = ['general','feature','important','regression','performance','usability']
verbs = ['do','make','execute','select','count','process','insert','validate','verify','filter','magnify']
words = ['abstraction','acetifier','acrodont','adenographical','advisableness','afterbreast','agrogeology',
         'albuminoscope','alkarsin','Alsophila','American','amphitheatral','anapnoic','angiography','annulation',
         'Anthoxanthum','antihelminthic','antisymmetrical','apoatropine','approximation','archgovernor','Arimaspian',
         'arthrospore','asportation','atangle','audiometric','autolaryngoscopy','awlwort','backspierer','ballast',
         'bargoose','Bathonian','becrawl','belatedness','bepaper','Bettina','bija','biriba','blastopore','blunge',
         'bony','Bourbon','brandreth','Britain','Bryum','bur','cabbagewood','calciocarnotite','Campodea','capitulum',
         'careener','cask','catstitch','censual','certify','chantey','chelydroid','chiromantical','chopa','Chrysotis',
         'circumgyrate','clausure','clot','cocculiferous','cogue','coloring','companator','concordancer','conjointment',
         'contemporary','coolness','cornigerous','costopleural','counterscrutiny','craniological','criniculture',
         'cryoscopy','cunye','cyclamin','cyton','dapple','debtorship','deedbox','delignification','denitrator',
         'dermatopnagic','detinet','dialogue','Dielytra','dioecious','discarnate','dishrag','dissertationist',
         'dochmiac','dopebook','drainable','dubitant','dynamometer','ecostate','Eimak','elephantoidal','Emilia',
         'enderonic','Enki','entreat','epimerite','equoidean','esophagoplasty','eudiometric','Evodia','existently',
         'extensional','facsimilist','fasciculus','feminacy','fickly','firepower','flawful','flunkeyize','forbiddable',
         'fork','frangula','frontomaxillary','furnishing','gallows','Gasterosteidae','Gemmingia','germanious',
         'girdlingly','glossoptosis','Goldbird','gracelessly','greatheart','gruelly','gurl','Haemogregarinidae',
         'handsomeness','hause','heedfulness','hemianopia','heptine','heterologous','highway','hoernesite',
         'homoiothermic','horseway','humulene','hydromaniac','hypercorrection','hypogean','ichthyal','illaudation',
         'impassioned','impuberal','incomprehension','indigitate','infare','iniquitously','insooth','intercombination',
         'interpiece','intranatal','iodinophilic','irritomotile','isotomous','jaragua','jocundity','just','janne',
         'Kedushshah','kiln','knowledging','labialization','lamboys','larkish','leadable','lenticularis','lexicologist',
         'Limnoria','lithogenetic','logographical','loxotic','lycanthropist','macrotous','malacodermatous',
         'manganeisen','Marianolatry','matador','mecometry','melastomaceous','merchantableness','Messiah','methylotic',
         'microphotoscope','milsey','Mikko','miscompute','mistranslation','mollycoddling','monolocular','mora',
         'mountainette','multimillion','Mussulwoman','myrmecology','Napoleonana','necrographer','nephrohydrosis',
         'newsprint','noble','nonchalky','nonelemental','nonmalignant','nonresident','nonvolcanic','nubbling',
         'obituarist','octary','oilcan','onca','opianyl','organizational','Ortol','Otomi','outroar','overcasting',
         'overgrow','overregister','overwrought','pachyphyllous','paleface','pancyclopedic','papion','parareka',
         'parsonese','patriarchalism','pedagogy','penetration','percolate','peripherically','perspiration',
         'Phalangerinae','philocatholic','photoceramics','phyllomorphy','picrorhizin','pinguid','placer',
         'platymesocephalic','plouky','poditti','polyaxial','polysporangium','porphyrin','postoperative','prankle',
         'precoloration','predivinity','prelusion','presalvation','prevaricatory','probeer','progger','proportionality',
         'Protoascales','prytanis','pseudospherical','publican','puppetize','pyrazolyl','quadruplex','quink',
         'radiocarbon','Ranquel','reaggregation','recessively','recurve','reforestize','reinstruct','renderable',
         'reprovably','respue','retrofracted','rhapsodie','rictus','robustly','rosoli','ruinator','sacciform','Salmon',
         'Santos','sauqui','scatterbrain','scirtopodous','scrawler','sealant','selaginellaceous','semiglobe','senaite',
         'serin','sextuplet','sheetwork','shortener','sighted','Singhalese','skelping','sleighty','Smithsonian',
         'soapbush','somacule','souper','spectator','spicular','splinder','spumiform','stainproof','stearin',
         'stethoscope','stoneworker','strich','stylite','subequality','subprincipal','succubine','sulphoterephthalic',
         'supereminent','superstrong','survivalism','swollenly','synecdochism','tactite','tangence','Tashnakist',
         'tectibranchiate','temporoalar','terral','Teutomania','theopneusty','thiofurane','thumblike','timbale',
         'tobaccoism','topmast','toxicemia','transconductance','treading','trichromat','triphammer','trophodynamic',
         'tubinarine','turnsheet','typographical','umbonule','unappeasedly','unbetray','unchangedness','unconditional',
         'uncurst','underfeature','undertie','undowny','uneviscerated','unflaunted','ungovernable','unicameralist',
         'unintersected','unlikelihood','unmollifiable','unpanel','unprecautioned','unreasonable','unride',
         'unserviceable','unspicy','unswept','untroubledly','unwillingness','upthunder','urtication','vallancy',
         'vegetation','vermiculite','victualer','visionist','voting','wany','Wazir','wheam','whuttering','wishedly',
         'workbasket','xenium','yen','zeuglodont','zygophoric']


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-l", "--libs", dest="libs",help="Number of test libraries", default=5)
    parser.add_option("-k", "--keywords", dest="keywords",help="Number of keywords in a test library", default=10)
    parser.add_option("-s", "--suites", dest="suites",help="Number of test suites", default=1)
    parser.add_option("-t", "--tests", dest="tests",help="Number of tests in a suite", default=10)
    parser.add_option("-f", "--resourcefiles", dest="resourcefiles",help="Number of resource files", default=1)
    parser.add_option("-r", "--resources", dest="resources",help="Number of resources in a file", default=30)
    parser.add_option("-v", "--validity", dest="validity",help="Validity of test cases (1...0). To have ~80% passes give 0.8. Default 1.", default=1)
    parser.add_option("-e", "--testdepth", dest="testdepth", help="Average number of steps in a test case (2..20)", default=3)
    parser.add_option("-d", "--dir", dest="dir",help="Target directory for the test project", default="theproject")
    (options, args) = parser.parse_args()

    sys.path.insert(0, '.')

    project_root_dir = os.path.join("./tmp/", options.dir + "/testdir/")
    sys.path.append(project_root_dir)
    shutil.rmtree(project_root_dir, ignore_errors=True)
    print "Test project is created into directory (option 'd'): %s" % project_root_dir

    if not os.path.exists(project_root_dir):
        os.makedirs(project_root_dir)
    try:
        assert main(project_root_dir, testlibs_count=int(options.libs), keyword_count=int(options.keywords),
            testsuite_count=int(options.suites), tests_in_suite=int(options.tests),
            resource_count=int(options.resourcefiles), resources_in_file=int(options.resources),
            avg_test_depth=int(options.testdepth), test_validity=float(options.validity))
    finally:
        #if len(args) >= 1 and ("del" in args):
        #    shutil.rmtree(dir, ignore_errors=True)
        #else:
        print "Not removing directory: " + project_root_dir
