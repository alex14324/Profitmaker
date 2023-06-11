# Clean duplicaes in files proceeded by service extractor
import sys
import os
from shutil import rmtree
from hashlib import md5, blake2b
import time

def rm_dups(input_dir, out_dir)-> tuple[int, int, int]:
    """Iter over input_dir's files and clean duplicated lines."""
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    start_time = time.time()
    proceeded_lines = 0
    unique_lines = 0
    for entry in os.scandir(input_dir):
        if entry.is_file():
            with open(entry.path, 'r', encoding="utf-8") as input_file:
                with open(os.path.join(out_dir, entry.name),
                          'w', encoding="utf-8") as out_file:
                    cleaned_lines = []
                    for line in input_file:
                        hd = blake2b(line.rstrip('\n').encode()).hexdigest()
                        proceeded_lines += 1
                        if hd not in cleaned_lines:
                            out_file.write(line)
                            cleaned_lines.append(hd)
                    unique_lines += len(cleaned_lines)
    rmtree(input_dir)
    start_time = time.time() - start_time
    return int(start_time), proceeded_lines, unique_lines


if __name__ == '__main__':
    input_dir = sys.argv[1]
    out_dir = sys.argv[2]
    start_time, proceeded_lines, unique_lines = rm_dups(input_dir, out_dir)

    print(f"Work done in {start_time}s.\n"
          f"Proceed {proceeded_lines} lines.\n"
          f"Unique lines: {unique_lines}.")



