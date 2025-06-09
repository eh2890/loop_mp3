import os
from contextlib import contextmanager
import pathlib
from typing import ContextManager


@contextmanager
def PushDir(dst_dir: pathlib.Path) -> ContextManager[None]:
    src_dir = os.getcwd()
    os.chdir(dst_dir)
    try:
        yield
    finally:
        os.chdir(src_dir)
