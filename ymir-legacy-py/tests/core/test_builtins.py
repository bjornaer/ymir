import os

from ymir.interpreter import YmirInterpreter


def run_script(interpreter, script_code):
    # Helper to run a script and capture the output
    # For now, we assume print() is the main way to get output
    # This might need to be adjusted based on interpreter's capabilities
    import io
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        # Create a temporary file to run the script
        # This is because the interpreter currently loads from files
        temp_script_path = "temp_test_script.ymr"
        with open(temp_script_path, "w") as temp_file:
            temp_file.write(script_code)

        interpreter.run_ymir_script(temp_script_path)

        os.remove(temp_script_path)

    return f.getvalue()


def test_builtin_math_functions(capsys):
    """
    Tests the functionality of the newly added built-in math functions.
    """
    interpreter = YmirInterpreter()
    script_code = """
module main
print(sqrt(16.0))
print(ceil(4.2))
print(floor(4.8))
print(log(1.0))
    """

    # Create a temporary file to run the script
    temp_script_path = "temp_builtin_math_test.ymr"
    with open(temp_script_path, "w") as temp_file:
        temp_file.write(script_code)

    # The run_ymir_script doesn't need to be wrapped to capture output
    # when using capsys. Pytest handles it.
    interpreter.run_ymir_script(temp_script_path)

    os.remove(temp_script_path)

    captured = capsys.readouterr()
    output = captured.out.strip().splitlines()

    # Filter out debug lines and get only the actual output
    actual_output = [line for line in output if not line.startswith("[DEBUG]")]

    assert "4.0" in actual_output[0]
    assert "5" in actual_output[1]
    assert "4" in actual_output[2]
    assert "0.0" in actual_output[3]
