import datetime

interval_units = [(60, 'minutes'), (60, 'hour'), (24, 'day'), (365, 'year')]

def tnow():
    return datetime.datetime.now().timestamp()

def sec_to_human(sec):
    parts = [[int(sec), 'second']]
    for (dur, unit) in interval_units:
        last = parts[-1]
        if last[0] == 0:
            break

        val = last[0] // dur
        parts[-1][0] -= (val * dur)

        parts.append([val, unit])

    done = 0
    res = []
    for val, unit in reversed(parts):
        if len(res) > 0:
            done += 1
            if done == 2:
                break

        if val == 0:
            continue

        if val > 1:
            unit += 's'

        part_fmt = '%d %s' % (val, unit)
        res.append(part_fmt)

    return ', '.join(res)
