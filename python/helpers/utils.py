# Small utility functions


import math
import itertools
import logging
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True


def clip(value, lower, upper):
    # clip a single numerical value between lower and upper
    return lower if value < lower else upper if value > upper else value


def deltaPhi(phi1, phi2):
    # calculate difference in azimutal angle.
    # note: result is forced to be in the range (-pi, pi)
    try:
        dphi = phi1 - phi2
    except TypeError:
        dphi = phi1.phi - phi2.phi
    while dphi > math.pi:
        dphi -= 2 * math.pi
    while dphi < -math.pi:
        dphi += 2 * math.pi
    return dphi


def getDigit(number, n):
    # get the n'th digit of a number (starting from the back at index 0)
    return number // 10**n % 10


def deltaR2(eta1, phi1, eta2=None, phi2=None):
    # calculate delta R squared.
    if eta2 is None:
        a, b = eta1, phi1
        return deltaR2(a.eta, a.phi, b.eta, b.phi)
    else:
        deta = eta1 - eta2
        dphi = deltaPhi(phi1, phi2)
        return deta * deta + dphi * dphi


def deltaR(eta1, phi1, eta2=None, phi2=None):
    # caclulate delta R.
    return math.sqrt(deltaR2(eta1, phi1, eta2, phi2))


def deltaEta(obj1, obj2):
    # calculate delta eta.
    # note: the result is forced to be positive.
    return abs(obj1.eta - obj2.eta)


def closest(obj, collection, presel=lambda x, y: True):
    # get the closest element from a given collection to a given object
    closes = None
    dr2min = 1e6
    for candidate in collection:
        if not presel(obj, candidate): continue
        dr2 = deltaR2(obj, candidate)
        if dr2 < dr2min:
            closest = candidate
            dr2min = dr2
    return (ret, math.sqrt(dr2min))


def polarP4(obj=None, pt='pt', eta='eta', phi='phi', mass='mass'):
    # get a ROOT.Math.PtEtaPhiMVector for a given object
    if obj is None: return ROOT.Math.PtEtaPhiMVector()
    pt_val = getattr(obj, pt) if pt else 0
    eta_val = getattr(obj, eta) if eta else 0
    phi_val = getattr(obj, phi) if phi else 0
    mass_val = getattr(obj, mass) if mass else 0
    return ROOT.Math.PtEtaPhiMVector(pt_val, eta_val, phi_val, mass_val)


def p4(obj=None, pt='pt', eta='eta', phi='phi', mass='mass'):
    # get a ROOT.Math.XYZTVector for a given object
    v = polarP4(obj, pt, eta, phi, mass)
    return ROOT.Math.XYZTVector(v.px(), v.py(), v.pz(), v.energy())


def sumP4(*args):
    # calculate the vector sum of given objects.
    # note: the returned object is of type ROOT.Math.PtEtaPhiMVector
    p4s = [polarP4(x) for x in args]
    return sum(p4s, ROOT.Math.PtEtaPhiMVector())


def p4_str(p):
    # get printable string of a vector of a given object
    return '(pt=%s, eta=%s, phi=%s, mass=%s)' % (p.pt(), p.eta(), p.phi(), p.mass())


def get_subjets(jet, subjetCollection, idxNames=('subJetIdx1', 'subJetIdx2')):
    # get the subjets of a given jet in a given subjet collection.
    # note: subjets are ordered by pt.
    subjets = []
    for idxname in idxNames:
        idx = getattr(jet, idxname)
        if idx >= 0:
            subjets.append(subjetCollection[idx])
    subjets = sorted(subjets, key=lambda x: x.pt, reverse=True)
    return subjets


def corrected_svmass(sv):
    pproj = polarP4(sv).P() * math.sin(sv.pAngle)
    return math.sqrt(sv.mass * sv.mass + pproj * pproj) + pproj


def transverseMass(obj, met):
    # get transverse mass of a given object + met system.
    try:
        cos_dphi = math.cos(deltaPhi(obj, met))
        return math.sqrt(2 * obj.pt * met.pt * (1 - cos_dphi))
    except TypeError:
        cos_dphi = math.cos(deltaPhi(obj.phi(), met.phi))
        return math.sqrt(2 * obj.pt() * met.pt * (1 - cos_dphi))


def minValue(collection, fallback=99):
    if len(collection) == 0:
        return fallback
    else:
        return min(collection)


def maxValue(collection, fallback=0):
    if len(collection) == 0:
        return fallback
    else:
        return max(collection)


def closest_pair(objs, func=lambda a, b: deltaR2(a, b), reverse=False, fallback=-1):
    # get closest pair of objects within a collection of objects
    # and according to a given distance definition.
    if len(objs) < 2: return None, fallback
    pairs = itertools.combinations(range(len(objs)), 2)
    combs = [((i, j), func(objs[i], objs[j])) for i, j in pairs]
    return (max if reverse else min)(combs, key=lambda x: x[1])


def configLogger(name, loglevel=logging.INFO, filename=None):
    # define a Handler which writes INFO messages or higher to the sys.stderr
    logger = logging.getLogger(name)
    logger.setLevel(loglevel)
    console = logging.StreamHandler()
    console.setLevel(loglevel)
    console.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
    logger.addHandler(console)
    if filename:
        logfile = logging.FileHandler(filename)
        logfile.setLevel(loglevel)
        logfile.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
        logger.addHandler(logfile)
