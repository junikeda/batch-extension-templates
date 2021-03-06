from xml.etree.ElementTree import Element, SubElement, ElementTree
import logging
import utils
import time
from datetime import datetime, timedelta
import threading

logger = logging.getLogger('rendering-log')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
file_handler = logging.FileHandler('template.log')
file_handler.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
# add the handlers to logger
logger.addHandler(file_handler)

# add console logger as well
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
logger.addHandler(consoleHandler)


def info(message: str):
    """
    Log 'msg % args' with severity 'INFO' to the logger file

    :param message: The info message that will be added to the logger file
    :type message: str
    """
    logger.info(message_with_thread(message))


def error(error_message: str):
    """
    Log 'msg % args' with severity 'ERROR' to the logger file

    :param error_message: The info message that will be added to the logger file
    :type error_message: str
    """
    logger.error(message_with_thread(error_message))


def warning(warning_message: str):
    """
    Log 'msg % args' with severity 'ERROR' to the logger file

    :param warning_message: The info message that will be added to the logger file
    :type warning_message: str
    """
    logger.warning(message_with_thread(warning_message))


def account_info(args: object):
    """
    Logs the account info

    :param args: A few of the arguments set on the command line
    :type args: ArgumentParser
    """
    info("Batch Account Name: {}".format(args.BatchAccountName))
    info("Batch Account URL: {}".format(args.BatchAccountUrl))
    info("Storage account: {}".format(args.StorageAccountName))
    info("Reading in the list of test in the : {} file".format(args.TestConfig))


def export_result(test_managers: 'list[test_manager.TestManager]', total_time: int):
    """
    Exports the a file that is that is similar to a pytest export file. This is consumed by
    Azure pipeline to generate a build report.

    :param test_managers: A collection of jobs that were run
    :type test_managers: List[test_managers.TestManager]
    :param total_time: The duration for all the tasks to complete
    :type total_time: int
      """
    failed_jobs = 0  # type: int
    info("Exporting test output file")
    root = Element('testsuite')

    for test in test_managers:
        child = SubElement(root, "testcase")
        # Add a message to the error
        child.attrib["name"] = str(test.raw_job_id)
        if test.status.test_state != utils.TestState.COMPLETE:
            failed_jobs += 1
            sub_child = SubElement(child, "failure")
            sub_child.attrib["message"] = str("Job [{}] failed due the ERROR: [{}]".format(
                test.job_id, test.status.test_state))

            sub_child.text = str(test.status.message)

        # Add the time it took for this test to compete.
        if test.total_duration is not None:
            info("Total Test duration '{}', Pool [{}] took '{}' to become available, Job [{}] ran for '{}', "
                 .format(test.total_duration, test.pool_id, test.pool_start_duration, test.job_id, test.job_run_duration))
            # If the job failed we set the duration to 0
            test_duration = "0:00:00"
            try:
                converted_time = time.strptime(
                    str(test.total_duration).split('.')[0], '%H:%M:%S')
                total_seconds = timedelta(hours=converted_time.tm_hour, minutes=converted_time.tm_min,
                                          seconds=converted_time.tm_sec).total_seconds()
                child.attrib["time"] = str(total_seconds)
            except ValueError:
                child.attrib["time"] = test_duration

        # job did not run, so the test did not run
        else:
            child.attrib["time"] = "0:00:00"

    root.attrib["failures"] = str(failed_jobs)
    root.attrib["tests"] = str(len(test_managers))

    root.attrib["time"] = str(total_time.total_seconds())
    tree = ElementTree(root)
    tree.write("Tests/output.xml")


def print_result(test_managers: 'list[test_manager.TestManager]'):
    """
    Outputs all the results of the tests into a log file, including their errors and the total number of tests
    that failed and passed

    :param test_managers: The collection of tests that were run
    :type test_managers: List[test_managers.TestManager]
    """
    info("Number of jobs run {}.".format(len(test_managers)))
    failed_tests = 0  # type: int
    for test_item in test_managers:
        if test_item.status.test_state != utils.TestState.COMPLETE:
            failed_tests += 1
            warning(
                "job {} failed because {} : {}".format(
                    test_item.job_id,
                    test_item.status.test_state,
                    test_item.status.message))

    if failed_tests == 0:
        info("All jobs ran successfully.")

    else:
        info("Number of jobs passed {} out of {}.".format(
            len(test_managers) - failed_tests, len(test_managers)))


def message_with_thread(message: str):
    """Add the thread ident to the start of a log message.
    
    :param message: The original log message
    :type message: str
    :return: The log message with the thread ident prefixed
    :rtype: str
    """
    return "Thread:{} - {}".format(threading.currentThread().ident, message)
