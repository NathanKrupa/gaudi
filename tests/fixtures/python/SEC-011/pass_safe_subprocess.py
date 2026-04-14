"""Passing fixture for SEC-011: argv-list form and literal commands."""

import os
import subprocess


def list_files(target: str):
    return subprocess.run(["ls", target], check=True)


def grep_pattern(pattern: str, path: str):
    return subprocess.Popen(["grep", pattern, path])


def run_literal_command():
    return subprocess.run("date", shell=True, check=True)


def os_system_literal():
    return os.system("sync")
