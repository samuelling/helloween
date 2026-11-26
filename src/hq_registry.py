HQ = {}


def hq(pid, tex=1024):
    def deco(fn):
        HQ[pid] = (fn, tex)
        return fn
    return deco
