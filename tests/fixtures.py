from pathlib import Path

CD = Path(__file__).parent
DATA = CD / "data"

def get_data_path_by_name(name):
    if name == "hello-world.exe":
        return DATA / "hello-world" / "hello-world.exe"

    raise ValueError("unknown test file")