from pathlib import Path
from server import Environment
import logging, sqlite3, secrets

env = Environment()

# load configuration files and initialize globals
configFile = Path(env.setdefault("CONFIG_LOCATION", "config.yml"))

version = {"major": 0, "minor": 0.1, "series": "Alpha"}

users_db = None

def hash_algorithm():
    return hashlib.sha256()

""" ----------------------------------------------------------------
"""
def init_user_db(filename):
    connection = sqlite3.connect(filename)
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE users (user_id text, pass_hash text, is_active integer)")
    connection.commit()
    connection.close()

def connect_user_db(filename):
    user_db_file = Path(filename)
    if not user_db_file.is_file():
        init_user_db(filename)
    global users_db
    users_db = user_db_file

connect_user_db("users.db")

report_requests = {}
settings = {}

def init_settings():
    global settings
    settings["approot"] = "/"
    settings["caching"] = "static/cache/"
    settings["cache_expiry"] = 604800
    settings["serving"] = "http://augur.chaoss.io/api/unstable"
    settings["pagination_offset"] = 25
    settings["reports"] = "reports.yml"
    settings["session_key"] = secrets.token_hex()
    settings["version"] = version

def write_settings(current_settings):
    current_settings["caching"] = str(current_settings["caching"])
    with open(configFile, 'w') as file:
        yaml.dump(current_settings, file)

""" ----------------------------------------------------------------
"""
def version_check(current_settings):
    def to_version_string(version_object):
        if version_object is None:
            return "Undefined_version"
        return f'{version_object["major"]}-{version_object["minor"]}-{version_object["series"]}'

    def update_from(old):
        if old == None:
            if "pagination_offset" not in current_settings:
                current_settings["pagination_offset"] = current_settings.pop("paginationOffset")
            if "session_key" not in current_settings:
                current_settings["session_key"] = secrets.token_hex()

        else:
            raise ValueError(f"Updating from {to_version_string(old)} to {to_version_string(version)} is unsupported")

        current_settings["version"] = version
        write_settings(current_settings)
        logging.info(f"Configuration updated from {to_version_string(old)} to {to_version_string(version)}")

    def compare_versions(old, new):
        if old["major"] < new["major"]:
            return -1, old["series"] == new["series"]
        elif old["major"] > new["major"]:
            return 1, old["series"] == new["series"]
        elif old["minor"] < new["minor"]:
            return -1, old["series"] == new["series"]
        elif old["minor"] > new["minor"]:
            return 1, old["series"] == new["series"]
        return 0, old["series"] == new["series"]

    if "version" not in current_settings:
        update_from(None)

    version_diff = compare_versions(current_settings["version"], version)

    if current_settings["version"] == version:
        return
    elif version_diff[0] == -1:
        update_from(current_settings["version"])
    elif version_diff[0] == 1:
        raise ValueError("Downgrading configuration versions is unsupported: " +
        f"from {to_version_string(current_settings['version'])} to {to_version_string(version)}")

    global settings
    settings = current_settings

# default reports definition
reports = {'pull_request_reports': [{'url': 'pull_request_reports/average_commits_per_PR/', 'description': 'Average commits per pull request'}, {'url': 'pull_request_reports/average_comments_per_PR/', 'description': 'Average comments per pull request'}, {'url': 'pull_request_reports/PR_counts_by_merged_status/', 'description': 'Pull request counts by merged status'}, {'url': 'pull_request_reports/mean_response_times_for_PR/', 'description': 'Mean response times for pull requests'}, {'url': 'pull_request_reports/mean_days_between_PR_comments/', 'description': 'Mean days between pull request comments'}, {'url': 'pull_request_reports/PR_time_to_first_response/', 'description': 'Pull request time until first response'}, {'url': 'pull_request_reports/average_PR_events_for_closed_PRs/', 'description': 'Average pull request events for closed pull requests'}, {'url': 'pull_request_reports/Average_PR_duration/', 'description': 'Average pull request duration'}], 'contributor_reports': [{'url': 'contributor_reports/new_contributors_bar/', 'description': 'New contributors bar graph'}, {'url': 'contributor_reports/returning_contributors_pie_chart/', 'description': 'Returning contributors pie chart'}], 'contributor_reports_stacked': [{'url': 'contributor_reports/new_contributors_stacked_bar/', 'description': 'New contributors stacked bar chart'}, {'url': 'contributor_reports/returning_contributors_stacked_bar/', 'description': 'Returning contributors stacked bar chart'}]}

# Initialize logging
format = "%(asctime)s: %(message)s"
logging.basicConfig(filename="augur_view.log", filemode='a', format=format, level=logging.INFO, datefmt="%H:%M:%S")
