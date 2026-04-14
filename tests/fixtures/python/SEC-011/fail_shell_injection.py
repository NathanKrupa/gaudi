"""Fixture for SEC-011: subprocess and os.system with untrusted command strings."""

import os
import subprocess


def run_ls(target: str):
    return subprocess.run(f"ls {target}", shell=True)


def popen_grep(pattern: str, path: str):
    return subprocess.Popen("grep " + pattern + " " + path, shell=True)


def check_output_cat(path: str):
    return subprocess.check_output("cat %s" % path, shell=True)


def call_system(user_cmd: str):
    return os.system(user_cmd)


def popen_system(user_cmd: str):
    return os.popen(user_cmd)
