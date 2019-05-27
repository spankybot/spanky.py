from tokenize import tokenize, OP, ENDMARKER
from token import N_TOKENS, NUMBER
from collections import OrderedDict, deque
from io import BytesIO

def extract_params(s):
    tokvals = deque([None, None, None])
    toknums = deque([None, None, None])
    decls = OrderedDict()

    g = tokenize(BytesIO(s.encode('utf-8')).readline)

    def add_decl(var_type, var_name):
        decls[var_name] = {}
        decls[var_name]["type"] = var_type
        decls[var_name]["default"] = None

    def set_defval(var_name, var_def):
        if var_name in decls:
            if decls[var_name]["type"] == "int":
                var_def = int(var_def)
            elif decls[var_name]["type"] == "float":
                var_def = float(var_def)
            decls[var_name]["default"] = var_def

    for toknum, tokval, _, _, _  in g:
        # Only trigger for : or =
        if toknums[-1] == OP:
            # If the operator is a : then it's a variable declaration
            if tokvals[-1] == ":":
                add_decl(tokvals[-2], tokval)
            # If the operator is a = then it's a default value
            elif tokvals[-1] == "=":
                set_defval(tokvals[-2], tokval)

        toknums.append(toknum)
        tokvals.append(tokval)

    # Implicit values should be specified at the end of the declaration
    has_defval = False
    for var in decls:
        if decls[var]["default"] != None:
            has_defval = True
        elif has_defval:
            raise ValueError("Implicit values must be specified at the end of the string")

    return decls

def map_params(s, params):
    try:
        if s.split()[-1].startswith("http"):
            s = " ".join(s.split()[0:-1])
    except:
        pass

    # TODO: this is discord specific
    if s.endswith(">"):
        s = s[0:s.rfind("<")]

    g = tokenize(BytesIO(s.strip().encode('utf-8')).readline)

    # Go through the parsed tokens and eliminate tokens used for string formatting
    input_toks = []
    for toknum, tokval, _, _, _ in g:
        if toknum > N_TOKENS or toknum == ENDMARKER:
            continue

        input_toks.append((tokval, toknum))

    # Create a dictionary with the implicit parameter values
    output_vals = OrderedDict()
    for var in params:
        output_vals[var] = params[var]["default"]

    # Go through the input
    intoks = deque([None])
    idx_in = 0
    idx_out = 0
    while idx_in < len(input_toks) and idx_out < len(output_vals):
        args = input_toks[idx_in][0]
        param = list(output_vals.keys())[idx_out]

        # If '-' operator is found, then look ahead of the inputs
        if args == "-" and idx_in != len(input_toks) - 1:
            idx_in += 1
            intoks.append(args)
            continue

        # Check if it's a number
        num_sign = 1
        if intoks[-1] == "-":
            if input_toks[idx_in][1] != NUMBER:
                args = intoks[-1] + args
            else:
                num_sign = -1

        if params[param]["type"] == "int":
            output_vals[param] = int(args) * num_sign
        elif params[param]["type"] == "float":
            output_vals[param] = float(args) * num_sign
        else:
            output_vals[param] = args

        idx_in += 1
        idx_out += 1
        intoks.append(args)

    return output_vals
