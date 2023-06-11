import json
import argparse
import multiprocessing as mp
import time
import os
from log_processor import LogProcessor
from termcolor import colored
import colorama

welcome_msg = """
______              __  _  _    ___  ___        _               
| ___ \            / _|(_)| |   |  \/  |       | |              
| |_/ /_ __  ___  | |_  _ | |_  | .  . |  __ _ | | __ ___  _ __ 
|  __/| '__|/ _ \ |  _|| || __| | |\/| | / _` || |/ // _ \| '__|
| |   | |  | (_) || |  | || |_  | |  | || (_| ||   <|  __/| |   
\_|   |_|   \___/ |_|  |_| \__| \_|  |_/ \__,_||_|\_\\___||_|   
"""

author_msg = """
                         _    
|_  \/   |/  o   | _ __ |_) _ 
|_) /    |\  | \_|(_)||||_)(_|
"""

class TaskFinder(mp.Process):
    """Iter over input dir(check for log dirs) and put to task queue path to the log dir."""
    task_queue: mp.Queue
    input_dir: str
    settings: dict

    def __init__(self, task_queue, settings: dict, input_dir: str):
        super(TaskFinder, self).__init__()
        self.task_queue = task_queue
        self.settings = settings
        self.input_dir = input_dir
        self.worker_count = settings.get("threads")
        self.total_logs = 0
        for _ in os.scandir(self.input_dir):
            self.total_logs += 1

    def get_total(self):
        return self.total_logs

    def run(self):
        st = time.time()

        print(colored(f"[+] TaskFinder report: found ", "green"),
              colored(f"{self.total_logs}", "yellow", attrs=["bold"]),
              colored(f"directories with logs.", "green"))

        for entry in os.scandir(self.input_dir):
            if entry.is_dir() and entry.name != '.' and entry.name != '..':
                self.task_queue.put(entry.path)

        for _ in range(self.worker_count):
            self.task_queue.put('-1')  # finish workers


class ResultWritter(mp.Process):
    result_queue: mp.Queue
    settings: dict
    out_dir: str
    """Get result from result_queue, and write it to disk."""

    def __init__(self,
                 result_queue: mp.Queue,
                 settings: dict,
                 out_dir: str):
        super(ResultWritter, self).__init__()
        self.queue = result_queue
        self.settings = settings
        self.out_dir = out_dir
        if not os.path.exists(self.out_dir):
            os.mkdir(self.out_dir)
        self.worker_count = settings.get("threads")
        self.total = 0

    def run(self) -> None:
        finish_counter = 0
        while True:
            if finish_counter == self.worker_count:
                break
            task = self.queue.get()
            if task == '-1':
                finish_counter += 1
                continue
            for key, value in task.items():
                with open(os.path.join(self.out_dir, key + '.txt'), 'a', encoding="utf-8") as out_file:
                    self.total += len(value)
                    out_file.writelines(value)

        print(colored(f"[+] ResultWritter report: wrote", "green"),
              f"{colored(str(self.total), 'yellow', attrs=['bold'])}",
              colored("lines.", "green"))


def worker(task_queue: mp.Queue,
           result_queue: mp.Queue,
           settings: dict,
           request: list
           ) -> None:
    """Process input log dir, check type of log and extract data."""
    lp = LogProcessor(settings.get("rules_path"))

    while True:
        task = task_queue.get()
        if task == '-1':
            result_queue.put('-1')
            break

        res = {}
        log = lp.process(task)
        if log is None:  # unknown format
            continue
        login_data = log.login_data

        for query in request:
            res[query] = []
            res[query] = [f"{ld[1]}:{ld[2]}\n" for ld in login_data if ld[0].find(query) != -1]

        result_queue.put(res)


if __name__ == '__main__':
    colorama.init()
    print(colored(welcome_msg, 'green', attrs=['bold']), colored(author_msg, 'red', attrs=['bold']))
    with open('settings.json', 'rb') as settings_file:
        settings = json.load(settings_file)
    with open('preset.json', 'r', encoding="utf-8") as preset_file:
        preset = json.load(preset_file)
    parser = argparse.ArgumentParser(description='Extract user:pass from logs directory for specified domains.\n'
                                                 'By @KijoRomBa:)')
    parser.add_argument('-i', metavar='input_dir', type=str,
                        help='input dir with logs.', required=False)
    parser.add_argument('-o', metavar='out_dir', type=str,
                        help='out_dir dir for extracted data.', required=False)
    args = parser.parse_args()
    out_dir = None
    if args.o is not None:
        out_dir = args.o
    else:
        out_dir = settings.get("out_dir")
    if args.i is not None:
        input_dir = args.i
    else:
        input_dir = settings.get("input_dir")
    preset_domains = []
    if preset.get("domain") != "":
        preset_domains.append(preset.get("domain"))
    preset_domains += preset.get("domain_list")
    manager = mp.Manager()

    task_queue = manager.Queue(666)
    result_queue = manager.Queue(666)

    tf = TaskFinder(task_queue, settings, input_dir)
    total_logs = tf.get_total()
    tf.start()
    rw = ResultWritter(result_queue, settings, out_dir)
    rw.start()

    pool = mp.Pool(settings.get("threads"))
    results = []
    st = time.time()
    for _ in range(settings.get("threads")):
        res = pool.apply_async(
            func=worker,
            args=(
                task_queue,
                result_queue,
                settings,
                preset_domains
            )
        )
        results.append(res)
    tf.join()
    [res.wait() for res in results]
    rw.join()
    work_time = time.time() - st
    
    print(colored(f"[+] Work done!", 'green'))
    print(colored(f"[+] Time elapsed:", "green"),
          f"{colored(str(round(work_time, 6)), 'yellow', attrs=['bold'])}",
          colored("seconds.", 'green'))
    print(colored(f"[+] Average time: ", "green"),
          f"{colored(str(round(work_time / total_logs, 6)), 'yellow', attrs=['bold'])}",
          colored(" s/log, ", "green"),
          f"{colored(str(round(total_logs / work_time, 2)), 'yellow', attrs=['bold'])}",
          colored(" log/s.", 'green'))

    print(colored(f"[$] For donations(BTC):", 'green'),
          f"{colored('bc1qngss0dd966q79rg5p286hgmnfhqnemtwps9r9m', 'red')}")
    print(colored(f"[@] For support: ", 'green') + colored('kijomba@exploit.im', "green", attrs=['bold']))
    colorama.deinit()
