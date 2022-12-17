import sys

import dnfile
import dnfile.signature


# heading
H="===="
# indent
I="    "


def main(fpath: str):
    pe = dnfile.dnPE(fpath)

    if not pe.net:
        return

    warns = pe.get_warnings()
    if warns:
        print(H, "WARNINGS:")
        for w in warns:
            print(I, w)
    for m in pe.net.methods:
        print(H, m.name)
        print(I, m.signature)
        if m.params:
            print(I, "Params:")
            for p in m.params:
                s = f"{I*2}{p.sequence} {p.name} {p.type_str}"
                for name, val in p.flags:
                    if val:
                        s += f" {name}"
                print(s)


if __name__ == "__main__":
    for fpath in sys.argv[1:]:
        print("----------", fpath)
        main(fpath)
