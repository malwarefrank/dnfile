from pathlib import Path

CD = Path(__file__).parent
DATA = CD / "data"


def get_data_path_by_name(name):
    if name == "hello-world.exe":
        return DATA / "hello-world" / "hello-world.exe"
    elif name == "ModuleCode_x86.exe":
        return DATA / "mixed-mode" / "ModuleCode" / "bin" / "ModuleCode_x86.exe"
    elif name == "EmptyClass_x86.exe":
        return DATA / "mixed-mode" / "EmptyClass" / "bin" / "EmptyClass_x86.exe"
    elif name == "EmptyClass_amd64.exe":
        return DATA / "mixed-mode" / "EmptyClass" / "bin" / "EmptyClass_amd64.exe"
    elif name == "1d41308bf4148b4c138f9307abc696a6e4c05a5a89ddeb8926317685abb1c241":
        return DATA / "malware" / "1d41308bf4148b4c138f9307abc696a6e4c05a5a89ddeb8926317685abb1c241"
    elif name == "387f15043f0198fd3a637b0758c2b6dde9ead795c3ed70803426fc355731b173.dll_":
        return DATA / "malware" / "387f15043f0198fd3a637b0758c2b6dde9ead795c3ed70803426fc355731b173.dll_"
    elif name == "7f4ba9fc95b30baf8922a6933a4ff1c6a7fef41fae487bb31014c4963357770f.dll_":
        return DATA / "malware" / "7f4ba9fc95b30baf8922a6933a4ff1c6a7fef41fae487bb31014c4963357770f.dll_"
    elif name == "minimal-res.exe":
        return DATA / "minimal-resource" / "bin" / "minimal-res.exe"

    raise ValueError("unknown test file")
