"""Module for processing and unifying data from different stealers"""

import json
from os import scandir
from os.path import join as path_join
from os.path import exists as path_exists
import codecs
from termcolor import colored

codecs.register_error("strict", codecs.ignore_errors)

stealers = [
    "redline",
    "racoon_v1",
    "type_1",
    "hunter",
    "type_2"
]


class Log:
    type: str  # redline racoon etc
    id: str
    login_data: list  # or list with tuples: url, usr, passw
    cookies: dict
    autofills: dict
    cc: dict
    file_grabber: dict


class LogProcessor:
    """Make a Log objects, based on parsed log dir."""
    def __init__(self, rules_path):
        with open(rules_path, 'rb') as jfile:
            self.rules = json.load(jfile)

    def get_signature_score(self, stealer_type, entry_list):
        sig_score = 0
        for entry in entry_list:
            if entry.name in self.rules[stealer_type]["signatures"]["files_dirs"]:
                sig_score += 1
        return sig_score

    def get_log_type(self, log_path) -> str:
        entr_l = [entry for entry in scandir(log_path)]
        sig_scores = {steal_type: self.get_signature_score(steal_type, entr_l) for steal_type in stealers}
        max_score = max(sig_scores, key=sig_scores.get)
        if sig_scores[max_score] < 3:
            print(colored(f"[-] Found unknown/bad log format! Send me this log.", 'red'))
            print(colored(f"[-] Unknown log: ", "red"),
                  colored(f"{log_path}", 'green', attrs=['bold']))
            return "unknown"
        else:
            return max_score

    def fill_logindata(self, log_type, log_path) -> list:
        if log_type != "unknown":
            login_data = []
            pass_rules = self.rules.get(log_type).get("passwords")
            pass_format = pass_rules.get("format")
            pass_process = pass_rules.get("process")
            passw_path = path_join(log_path, pass_rules["path"])
            if path_exists(passw_path):
                with open(passw_path, 'r', encoding="utf-8") as passw_file:
                    prev_url = ""
                    prev_user = ""
                    passw = ""
                    for line in passw_file:
                        if line.find(pass_format["url"]) != -1:
                            prev_url = eval(pass_process["url"])
                        if line.find(pass_format["user"]) != -1:
                            prev_user = eval(pass_process["user"])
                        if line.find(pass_format["passw"]) != -1:
                            passw = eval(pass_process["passw"])
                            login_data.append((prev_url, prev_user, passw))
                            prev_url = ""
                            prev_user = ""
                            passw = ""
            return login_data

    def process(self, log_path):
        log_type = self.get_log_type(log_path)
        # print(f"Log: {log_path} has a type: {log_type}")
        if log_type != "unknown":
            log = Log()
            log.type = log_type
            log.login_data = self.fill_logindata(log_type, log_path)
            return log
        return None
