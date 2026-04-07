# Fixture for SEC-004 EvalExecUsage.

def run_user_code(code_string):
    # POSITIVE: eval call
    return eval(code_string)


def run_user_script(script):
    # POSITIVE: exec call
    exec(script)


def safe_alternative(expression):
    # NEGATIVE: ast.literal_eval is fine
    import ast
    return ast.literal_eval(expression)


def use_compile(source):
    # NEGATIVE: compile() is not flagged
    return compile(source, "<string>", "exec")
