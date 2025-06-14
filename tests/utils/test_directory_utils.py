import tempfile
import pathlib

from utils.directory_utils import PushDir


class TestPushDir:
    def test_pushdir_changes_directory_and_restores(self) -> None:
        original_dir = pathlib.Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            with PushDir(tmp_path):
                assert pathlib.Path.cwd().resolve() == tmp_path.resolve()
            assert pathlib.Path.cwd().resolve() == original_dir.resolve()

    def test_pushdir_restores_dir_on_exception(self) -> None:
        original_dir = pathlib.Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            try:
                with PushDir(tmp_path):
                    assert pathlib.Path.cwd().resolve() == tmp_path.resolve()
                    raise ValueError("Testing exception inside PushDir")
            except ValueError:
                pass
            assert pathlib.Path.cwd().resolve() == original_dir.resolve()
