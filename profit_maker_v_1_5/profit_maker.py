import os
import sys
from multiprocessing import Pool, Queue, Manager, Process
from tldextract import extract
import time
import argparse
from dup_cleaner3 import rm_dups
from termcolor import colored
from halo import Halo
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

kiromba_anim = {
        "interval": 180,
        "frames": [
            "}=>▐$$CASH$BTC$CASH$BTC$CASH$BTC$CASH$BTC$$▌<={",
            "}=>▐_______________________________________▌<={",
            "}=>▐P______________________________________▌<={",
            "}=>▐_pR____________________________________▌<={",
            "}=>▐__prO__________________________________▌<={",
            "}=>▐___proF________________________________▌<={",
            "}=>▐____profI______________________________▌<={",
            "}=>▐_____profiT____________________________▌<={",
            "}=>▐______profit$__________________________▌<={",
            "}=>▐_______profit$C________________________▌<={",
            "}=>▐________profit$cO______________________▌<={",
            "}=>▐_________profit$coM____________________▌<={",
            "}=>▐__________profit$comE__________________▌<={",
            "}=>▐___________profit$comeS________________▌<={",
            "}=>▐____________profit$comes$______________▌<={",
            "}=>▐_____________profit$comes$T____________▌<={",
            "}=>▐______________profit$comes$tO__________▌<={",
            "}=>▐_______________profit$comes$to$________▌<={",
            "}=>▐________________profit$comes$to$Y______▌<={",
            "}=>▐_________________profit$comes$to$yo____▌<={",
            "}=>▐__________________profit$comes$to$you__▌<={",
            "}=>▐___________________profit$comes$to$you$▌<={",
            "}=>▐_______________________________________▌<={",
            "}=>▐$PROFIT!$PROFIT!$PROFIT!$PROFIT!$PROFIT▌<={",
            "}=>▐_______________________________________▌<={",
            "}=>▐PROFIT!$PROFIT!$PROFIT!$PROFIT!$PROFIT!▌<={",
            "}=>▐_______________________________________▌<={",
            "}=>▐ROFIT!$PROFIT!$PROFIT!$PROFIT!$PROFIT!$▌<={",
            "}=>▐_______________________________________▌<={",
            "}=>▐___________________profit$comes$to$you$▌<={",
            "}=>▐___________________profit$comes$to$you$▌<={",
            "}=>▐__________________profit$comes$to$you__▌<={",
            "}=>▐_________________profit$comes$to$yo____▌<={",
            "}=>▐________________profit$comes$to$y______▌<={",
            "}=>▐_______________profit$comes$to$________▌<={",
            "}=>▐______________profit$comes$to______D___▌<={",
            "}=>▐_____________profit$comes$t_______OD___▌<={",
            "}=>▐____________profit$comes$________NOD___▌<={",
            "}=>▐___________profit$comes_________ANOD___▌<={",
            "}=>▐__________profit$come__________TANOD___▌<={",
            "}=>▐_________profit$co___________$ETANOD___▌<={",
            "}=>▐________profit$c____________D$_________▌<={",
            "}=>▐_______profit$_____________DO$_________▌<={",
            "}=>▐______profit______________DON$_________▌<={",
            "}=>▐_____profi_______________DONA$_________▌<={",
            "}=>▐____prof________________DONAT$_________▌<={",
            "}=>▐___pro_________________DONATE__________▌<={",
            "}=>▐__pr__________________DONATE$__________▌<={",
            "}=>▐_p__________________$DONATE$___________▌<={",
            "}=>▐_______________________________________▌<={",
            "}=>▐$$CASH$BTC$CASH$BTC$CASH$BTC$CASH$BTC$$▌<={",
        ]
    }

class TaskFinder(Process):
    queue: Queue
    input_dir: str
    worker_count: int
    """Iter over input dir, find ogs folders, and put tham to task_queue."""

    def __init__(self, input_dir: str, task_queue: Queue, worker_count: int):
        super(TaskFinder, self).__init__()
        if not os.path.exists(input_dir):
            print("[-] Input dir missing!")
            sys.exit(-1)
        self.input_dir = input_dir
        self.queue = task_queue
        self.worker_count = worker_count
        self.total = 0

    def run(self) -> None:
        # print("TaskFinder here.")
        start_time = time.time()
        counter = 0
        for _ in os.scandir(self.input_dir):
            counter += 1
        self.total = counter
        print(colored(f"[+] TaskFinder report: found ", "green"), colored(f"{self.total}", "yellow", attrs=["bold"]), colored(f"directories with logs.", "green"))
        with Halo(text=colored("(ง •̀_•́)ง !", "cyan", attrs=["bold"]), spinner=kiromba_anim):
            for entry in os.scandir(self.input_dir):
                if entry.is_dir() and entry.name != '.' and entry.name != '..':
                    # got log dir
                    pass_path = os.path.join(entry.path, "Passwords.txt")
                    cookies_path = ''
                    info_path = ''
                    geo = entry.name[0] + entry.name[1]
                    for sub_entry in os.scandir(entry.path):
                        if sub_entry.is_dir and "ookies" in sub_entry.name:
                            cookies_path = sub_entry.path
                        if sub_entry.is_file() and "info" in sub_entry.name.lower():
                            info_path = sub_entry.path
                    if os.path.exists(pass_path):
                        self.queue.put((pass_path, cookies_path, info_path, geo))
            for _ in range(self.worker_count):
                self.queue.put(('-1', '-1', '-1'))  # finish work
        start_time = time.time() - start_time


class ResultWritter(Process):
    result_queue: Queue
    out_dir: str
    worker_count: int
    add_url: bool
    put_geo: bool
    put_ip: bool
    splitter: str
    """Get result from result_queue, and write it to disk."""

    def __init__(self, out_dir: str,
                 result_queue: Queue,
                 worker_count: int,
                 add_url: bool,
                 put_ip: bool,
                 put_geo: bool,
                 splitter: str):
        super(ResultWritter, self).__init__()
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        self.out_dir = out_dir
        self.queue = result_queue
        self.worker_count = worker_count
        self.total = 0
        self.add_url = add_url
        self.put_ip = put_ip
        self.put_geo = put_geo
        self.splitter = splitter

    def run(self) -> None:
        start_time = time.time()
        finish_counter = 0
        while True:
            task: tuple
            if finish_counter == self.worker_count:
                break
            task = self.queue.get()
            if task[0] == '-1':
                finish_counter += 1
                continue

            geo, user_ip, domain, user, passw = task
            if self.put_ip:
                user_ip = user_ip + ':'
                geo = ''
            elif self.put_geo:
                geo = geo + ':'
                user_ip = ''
            res_path = os.path.join(self.out_dir, domain + '.txt')
            with open(res_path, 'a', encoding="utf-8") as res_file:
                if self.add_url:
                    res_file.write("".join([user_ip, geo, domain, self.splitter, user, self.splitter, passw, '\n']))
                else:
                    res_file.write("".join([user_ip, geo, user, self.splitter, passw, '\n']))
            self.total += 1
        start_time = time.time() - start_time
        print(colored(f"[+] ResultWritter report: proceed", "green"), f"{colored(str(self.total), 'yellow', attrs=['bold'])}", colored("entries.", "green"))


def worker_func(task_queue: Queue,
                result_queue: Queue,
                spec_domain: str,
                spec_domain_list: list,
                put_ip: bool) -> None:
    """Process single passw file, and put intermediate res to result_queue."""
    while True:
        task = task_queue.get()  # task - path to Passwords.txt file
        if task == ('-1', '-1', '-1'):
            result_queue.put(('-1', '-1', '-1'))
            break
        start_time = time.time()
        passw_file, cookies_file, info_file, geo = task
        user_ip = ''
        if put_ip and os.path.exists(info_file):
            with open(info_file, 'r', encoding="utf-8") as info_f:
                for line in info_f:
                    if 'ip' in line.lower():
                        user_ip = line.split(': ')[1].rstrip('\n')
                        break

        with open(passw_file, 'r', encoding="utf-8") as pass_file:
            prev_url = ''
            prev_usr = ''
            for line in pass_file:
                if line.startswith("URL"):
                    prev_url = line.rstrip('\n').split(": ")[1]
                if line.startswith("User"):
                    prev_usr = line.rstrip('\n').split(": ")[1]
                if line.startswith("Pass"):
                    _, domain, zone = extract(prev_url)  # strip url to domain
                    domain = domain + '.' + zone
                    if spec_domain is not None:
                        if domain != spec_domain:
                            prev_url = ''
                            prev_usr = ''
                            continue
                    if spec_domain_list is not None:
                        if domain not in spec_domain_list:
                            prev_url = ''
                            prev_usr = ''
                            continue
                    result_queue.put((geo,
                                      user_ip,
                                      domain,
                                      prev_usr,
                                      line.rstrip('\n').split(": ")[1]
                                      ))
                    prev_url = ''
                    prev_usr = ''
        start_time = time.time() - start_time
        # print(start_time) #  perfomance test


if __name__ == '__main__':
    colorama.init()
    print(colored(welcome_msg, 'green', attrs=['bold']),colored(author_msg, 'red', attrs=['bold']))

    parser = argparse.ArgumentParser(description='Extract data from logs directory.\nBy @KijoRomBa:)')
    parser.add_argument('input_dir', metavar='input_dir', type=str,
                        help='input dir with logs')
    parser.add_argument('out_dir', metavar='out_dir', type=str,
                        help='out_dir dir for extracted data')
    parser.add_argument('-t', dest='thread_count', metavar='thread_count', type=int,
                        help='count of workers (default 10)', nargs='?', default=10)
    parser.add_argument('-u', dest="add_url", type=bool,
                        help='1 - add url to output string, host:user:pass (default 0 - user:pass)',
                        nargs='?', default=False)
    parser.add_argument('-i', dest="put_ip", type=bool,
                        help='1 - add ip to output string, doesn`t work with -g',
                        nargs='?', default=False)
    parser.add_argument('-g', dest="put_geo", type=bool,
                        help='1 - add country code to output string, doesn`t work with -i',
                        nargs='?', default=False)
    parser.add_argument('-s', dest='splitter', metavar='splitter', type=str,
                        help='splitter for data(default ":")',
                        nargs='?', default=':')
    parser.add_argument('-d', dest='domain', metavar='domain', type=str,
                        help='extract only specified domain',
                        nargs='?')
    parser.add_argument('-f', dest='domain_list', metavar='domain_list', type=str,
                        help='extract only specified in file domains',
                        nargs='?')
    parser.add_argument('-r', dest='rem_dup', metavar='remove_dups', type=str,
                        help='remove duplicate strings',
                        nargs='?')

    args = parser.parse_args()

    input_dir = args.input_dir
    out_dir = args.out_dir
    worker_count = args.thread_count
    domain_list = None
    if args.domain_list is not None:
        with open(args.domain_list, 'r', encoding="utf-8") as domain_file:
            domain_list = [line.rstrip('\n') for line in domain_file.readlines()]

    pool = Pool(
        processes=worker_count,
    )
    manager = Manager()
    task_queue = manager.Queue(worker_count)
    result_queue = manager.Queue(worker_count*3)
    task_finder = TaskFinder(input_dir, task_queue, worker_count)
    task_finder.start()
    result_writter = ResultWritter(out_dir=out_dir,
                                   result_queue=result_queue,
                                   worker_count=worker_count,
                                   splitter=args.splitter,
                                   add_url=args.add_url,
                                   put_ip=args.put_ip,
                                   put_geo=args.put_geo)
    result_writter.start()
    results = []
    for _ in range(worker_count):
        res = pool.apply_async(
            func=worker_func,
            args=(
                task_queue,
                result_queue,
                args.domain,
                domain_list,
                args.put_ip,
            )
        )
        results.append(res)
    start_time = time.time()
    task_finder.join()
    result_writter.join()
    end_time = time.time()
    clean_time, proceeded_lines, unique_lines = 0, 0, 0
    if args.rem_dup:
        clean_time, proceeded_lines, unique_lines = rm_dups(out_dir, out_dir+'_clean')
    work_time = end_time - start_time
    print(colored(f"[+] Work done!", 'green'))
    print(colored(f"[+] Time elapsed:", "green"),
          f"{colored(str(int(work_time)), 'yellow', attrs=['bold'])}",
          colored("seconds.", 'green'))
    if args.rem_dup:
        print(colored(f"[C] Cleaner: proceed", 'green'),
              f"{colored(str(proceeded_lines), 'yellow', attrs=['bold'])}",
              colored(f"lines, unique:", 'green'),
              f"{colored(str(unique_lines), 'yellow', attrs=['bold'])}",
              colored(", time spend:", 'green'),
              f"{colored(str(clean_time), 'yellow', attrs=['bold'])}",
              colored("seconds.", 'green'))
    print(colored(f"[$] For donations(BTC):", 'green'), f"{colored('bc1qngss0dd966q79rg5p286hgmnfhqnemtwps9r9m', 'red')}")
    print(colored(f"[@] For support: ", 'green') + colored('kijomba@exploit.im', "green", attrs=['bold']))
    colorama.deinit()
