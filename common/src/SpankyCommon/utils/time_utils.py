import datetime
import pytz

time_tokens = ["s", "m", "h", "d"]
SEC_IN_MIN = 60
SEC_IN_HOUR = SEC_IN_MIN * 60
SEC_IN_DAY = SEC_IN_HOUR * 24
SEC_IN_YEAR = (
    SEC_IN_HOUR * 24 * 365
)  # yeah, maybe there aren't 365 days in one year

interval_units = [(60, "minute"), (60, "hour"), (24, "day"), (365, "year")]


def tnow():
    return datetime.datetime.now().timestamp()


def timeout_to_sec(stime):
    """
    Convert expressions such as 1h10s or 1d to seconds
    """
    total_seconds = 0

    last_start = 0
    for pos, char in enumerate(stime):
        if char in time_tokens:
            value = int(stime[last_start:pos])
            if char == "s":
                total_seconds += value
            elif char == "m":
                total_seconds += value * SEC_IN_MIN
            elif char == "h":
                total_seconds += value * SEC_IN_HOUR
            elif char == "d":
                total_seconds += value * SEC_IN_DAY
            elif char == "y":
                total_seconds += value * SEC_IN_YEAR

            last_start = pos + 1

    return total_seconds


def sec_to_human(sec):
    """
    Convert seconds to human readable strings (e.g. 100 seconds to 1 minute, 40 seconds)
    """
    if sec == 0:
        return "0 seconds"

    parts = [[int(sec), "second"]]
    for (dur, unit) in interval_units:
        last = parts[-1]
        if last[0] == 0:
            break

        val = last[0] // dur
        parts[-1][0] -= val * dur

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
            unit += "s"

        part_fmt = "%d %s" % (val, unit)
        res.append(part_fmt)

    return ", ".join(res)


def datetime_to_ts(dt):
    return int(
        (
            dt.replace(tzinfo=pytz.utc)
            - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)
        ).total_seconds()
    )
