import os
from contextlib import contextmanager
import pathlib
from typing import Iterator


@contextmanager
def PushDir(dst_dir: pathlib.Path) -> Iterator[None]:
    src_dir = os.getcwd()
    os.chdir(dst_dir)
    try:
        yield
    finally:
        os.chdir(src_dir)
