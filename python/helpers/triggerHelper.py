# Utility functions for triggers


def _pass_trig(event, trig):
    # return True only if trig exist and is 1
    try:
        if getattr(event, trig):
            return True
    except RuntimeError:
        pass
    return False


def passTrigger(event, trig_names):
    # check if an event passes any of a list of trigger names.
    # note: trig_names can be a list of trigger names,
    #       or a single trigger name.
    # note: if a trigger does not exist for the event,
    #       the event is considered to fail that trigger.
    if not isinstance(trig_names, (list, tuple)):
        trig_names = [trig_names]
    for trig in trig_names:
        if not hasattr(event, trig): continue
        if getattr(event, trig): return True
        else: continue
    return False
