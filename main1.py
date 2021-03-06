
#cmd ------>type :  "python main.py --input_dir input/ --output_dir output/"
import argparse
import logging
import os
import subprocess
import sys
import json

from constants import DEFAULT_OUTPUT_DIRECTORY_NAME, VALID_IMAGE_EXTENSIONS, WINDOWS_CHECK_COMMAND, \
    DEFAULT_CHECK_COMMAND, TESSERACT_DATA_PATH_VAR

import xmltodict
import io
from collections import OrderedDict
import xmljson
from lxml.etree import fromstring, tostring


def writeToJSONFile(path, fileName, data):
    filename_without_extension = os.path.splitext(fileName)[0]
    filePathNameWExt = path + filename_without_extension + '.json'
    with open(filePathNameWExt, 'w') as fp:
        json.dump(data, fp)


def create_directory(path):
    """
    Create directory at given path if directory does not exist
    :param path:
    :return:
    """
    if not os.path.exists(path):
        os.makedirs(path)


def check_path(path):
    """
    Check if file path exists or not
    :param path:
    :return: boolean
    """
    return bool(os.path.exists(path))


def get_command():
    """
    Check OS and return command to identify if tesseract is installed or not
    :return:
    """
    if sys.platform.startswith('win'):
        return WINDOWS_CHECK_COMMAND
    return DEFAULT_CHECK_COMMAND


def run_tesseract(filename, output_path, image_file_name):
    # Run tesseract
    filename_without_extension = os.path.splitext(filename)[0]
    text_file_path = os.path.join(output_path+"/", filename_without_extension)
    subprocess.run(['tesseract', image_file_name, text_file_path],
                   stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE)
    subprocess.run(['tesseract', image_file_name, text_file_path, "alto"],
                   stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE)

def check_pre_requisites_tesseract():
    """
    Check if the pre-requisites required for running the tesseract application are satisfied or not
    :param : NA
    :return: boolean
    """
    check_command = get_command()
    logging.debug("Running `{}` to check if tesseract is installed or not.".format(check_command))

    result = subprocess.run([check_command, 'tesseract'], stdout=subprocess.PIPE)
    if not result.stdout:
        logging.error("tesseract-ocr missing, install `tesseract` to resolve. Refer to README for more instructions.")
        return False

    logging.debug("Tesseract correctly installed!\n")

    if sys.platform.startswith('win'):
        environment_variables = os.environ
        logging.debug(
            "Checking if the Tesseract Data path is set correctly or not.\n")
        if TESSERACT_DATA_PATH_VAR in environment_variables:
            if environment_variables[TESSERACT_DATA_PATH_VAR]:
                path = environment_variables[TESSERACT_DATA_PATH_VAR]
                logging.debug("Checking if the path configured for Tesseract Data Environment variable `{}` \
                as `{}` is valid or not.".format(TESSERACT_DATA_PATH_VAR, path))
                if os.path.isdir(path) and os.access(path, os.R_OK):
                    logging.debug("All set to go!")
                    return True
                else:
                    logging.error(
                        "Configured path for Tesseract data is not accessible!")
                    return False
            else:
                logging.error("Tesseract Data path Environment variable '{}' configured to an empty string!\
                ".format(TESSERACT_DATA_PATH_VAR))
                return False
        else:
            logging.error("Tesseract Data path Environment variable '{}' needs to be configured to point to\
            the tessdata!".format(TESSERACT_DATA_PATH_VAR))
            return False
    else:
        return True


def main(input_path, output_path, file_type):
    # Check if tesseract is installed or not
    if not check_pre_requisites_tesseract():
        return

    # Check if a valid input directory is given or not
    if not check_path(input_path):
        logging.error("Nothing found at `{}`".format(input_path))
        return
    # Create output directory
    create_directory(output_path)

    # Check if input_path is directory or file
    if os.path.isdir(input_path):

        # Check if input directory is empty or not
        total_file_count = len(os.listdir(input_path))
        if total_file_count == 0:
            logging.error("No files found at your input location")
            return

        # Iterate over all images in the input directory
        # and get text from each image
        other_files = 0
        successful_files = 0

        data = {}
        f2 = open(output_path + "output.txt", "w")
        logging.info("Found total {} file(s)\n".format(total_file_count))

        for ctr, filename in enumerate(os.listdir(input_path)):
            logging.debug("Parsing {}".format(filename))
            extension = os.path.splitext(filename)[1]

            if extension.lower() not in VALID_IMAGE_EXTENSIONS:
                other_files += 1
                continue

            image_file_name = os.path.join(input_path, filename)
            run_tesseract(filename, output_path, image_file_name)
            successful_files += 1

            filename_without_extension = os.path.splitext(filename)[0]
            fn = output_path + "/" + filename_without_extension + ".txt"
            f = open(fn, encoding="utf8")
            psk = f.read()
            sk = psk.split("\n")
            for i in sk:
                if(i!=""and i!=" "):
                    f2.write(i)
                    f2.write("\n")


        f2 = open(output_path + "output.txt", "r")
        filetolist = f2.read().split("\n")


        #writeToJSONFile(output_path, "New", data)


        logging.info("Parsing Completed!\n")


        if successful_files == 0:
            logging.error("No valid image file found.")
            logging.error("Supported formats: [{}]".format(
                ", ".join(VALID_IMAGE_EXTENSIONS)))
        else:
            logging.info(
                "Successfully parsed images: {}".format(successful_files))
            logging.info(
                "Files with unsupported file extensions: {}".format(other_files))

    else:
        filename = os.path.basename(input_path)
        run_tesseract(filename, output_path, filename)



    #####################################Alto to json ########################################

    rootDir = output_path
    for dirName, subdirList, fileList in os.walk(rootDir):
        print('Found directory: %s' % dirName)
        print('Found sub-directory: %s' % subdirList)
        textblocks={}
        textline =""
        block=0
        for fname in fileList:
            if fname.endswith('xml'):
                fullpath = os.path.join(rootDir, dirName, fname)
                print(fullpath)
                with open(fullpath,'rb') as fd:
                    doc = xmltodict.parse(fd.read())

                    #xml = fromstring(fd.read())
                    #doc = xmljson.badgerfish.data(xml)
                fd.close()
                sarja = fname[0:9]

                try:

                    docx = doc['alto']['Layout']['Page']['PrintSpace']['TextBlock']

                    if type(docx) is list:
                        for b in docx:
                            textblocks['textblock'+str(block)]={}
                            line=0
                            if type(b['TextLine']) is list:
                                for l in b['TextLine']:
                                    if type(l['String']) is list:
                                        for s in l['String']:
                                            textline += s['@CONTENT']+" "
                                    else:# that means OrderedDict, one string inside TextLine
                                        textline += l['String']['@CONTENT']+ " "
                                    textblocks['textblock'+str(block)]['textline'+str(line)] = textline
                                    textline = ""
                                    line+=1
                            else: # that means OrderedDict
                                if type(b['TextLine']['String']) is list:
                                    for s in b['TextLine']['String']:
                                        textline += s['@CONTENT'] + " "
                                else:# that means OrderedDict, one string inside TextLine
                                    textline += b['TextLine']['String']['@CONTENT'] + " "
                                textblocks['textblock'+str(block)]['textline'+str(line)] = textline
                                textline = ""
                                line+=1
                            block +=1
                    else: # that means OrderedDict, textblock is one
                        textblocks['textblock'+str(block)]={}
                        line = 0
                        if type(docx['TextLine']) is list:
                            for l in docx['TextLine']:
                                if type(l['String']) is list:
                                    for s in l['String']:
                                        textline += s['@CONTENT']+" "
                                else:# that means OrderedDict, one string inside TextLine
                                    textline += l['String']['@CONTENT']+ " "
                                textblocks['textblock'+str(block)]['textline'+str(line)] = textline
                                textline = ""
                                line+=1
                        else: # that means OrderedDict
                            if type(docx['TextLine']['String']) is list:
                                for s in docx['TextLine']['String']:
                                    textline += s['@CONTENT'] + " "
                            else:# that means OrderedDict, one string inside TextLine
                                textline += docx['TextLine']['String']['@CONTENT']+" "
                            textblocks['textblock'+str(block)]['textline'+str(line)] = textline
                            textline = ""
                            line+=1
                        block +=1

                    data = {
                        'textblocks':textblocks
                    }
                except KeyError:
                    data = {
                        'text' : 'KeyError'
                    }
            else:
                print('Skipping file...')
    print(output_path+'data.json')
    with open(output_path+'data.json','a+') as outfile:
        json.dump(data, outfile, sort_keys=False)
        outfile.write('\n')
    outfile.close()
    data = {}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', help="Input directory where input images are stored")
    parser.add_argument('--input_file', help="Input image filepath")
    parser.add_argument('--output_dir', help="(Optional) Output directory for converted text")
    parser.add_argument('--f', help="(Optional) output file format")
    parser.add_argument('--debug', action='store_true', help="Enable verbose DEBUG logging")

    args = parser.parse_args()
    if not args.input_dir and not args.input_file:
        parser.error('Required either --input_file or --input_dir')

    if args.input_dir:
        input_path = os.path.abspath(args.input_dir)
    else:
        input_path = os.path.abspath(args.input_file)

    if args.f:
        file_type = args.f

    else:
        file_type = "hocr"


    if args.output_dir:
        output_path = os.path.abspath(args.output_dir)
    else:
        if os.path.isdir(input_path):
            output_path = os.path.join(input_path, DEFAULT_OUTPUT_DIRECTORY_NAME)
        else:
            dir_path = os.path.dirname(input_path)
            output_path = os.path.join(dir_path, DEFAULT_OUTPUT_DIRECTORY_NAME)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    # Check Python version
    if sys.version_info[0] < 3:
        logging.error("You are using Python {0}.{1}. Please use Python>=3".format(
            sys.version_info[0], sys.version_info[1]))
        exit()

    main(input_path, output_path, file_type)
