import os
import tempfile

from ymir.interpreter import YmirInterpreter


class TestMatrixOperations:
    def setup_method(self):
        self.interpreter = YmirInterpreter(verbosity="WARNING")

    def test_matrix_create(self):
        """Test matrix creation with specified dimensions and value."""
        script = """
        module test_matrix_create

        import stdlib.math

        # Test creating a 2x3 matrix filled with 5.0
        var matrix1: matrix[float] = stdlib.math.matrix_create(2, 3, 5.0)
        print("matrix1 =", matrix1)

        # Test creating a 3x2 matrix filled with 0.0
        var matrix2: matrix[float] = stdlib.math.matrix_create(3, 2, 0.0)
        print("matrix2 =", matrix2)

        # Test creating a 1x1 matrix filled with 1.0
        var matrix3: matrix[float] = stdlib.math.matrix_create(1, 1, 1.0)
        print("matrix3 =", matrix3)
        """

        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ymr", delete=False) as f:
            f.write(script)
            temp_file = f.name

        try:
            # Capture output
            import io
            from contextlib import redirect_stdout

            f = io.StringIO()
            with redirect_stdout(f):
                self.interpreter.run_ymir_script(temp_file)

            output = f.getvalue()

            # Check that matrices were created with correct dimensions and values
            assert "matrix1 = [[5.0, 5.0, 5.0], [5.0, 5.0, 5.0]]" in output
            assert "matrix2 = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]" in output
            assert "matrix3 = [[1.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_zeros(self):
        """Test matrix creation filled with zeros."""
        script = """
        module test_matrix_zeros

        import stdlib.math

        # Test creating a 2x3 matrix filled with zeros
        var matrix1: matrix[float] = stdlib.math.matrix_zeros(2, 3)
        print("matrix1 =", matrix1)

        # Test creating a 3x2 matrix filled with zeros
        var matrix2: matrix[float] = stdlib.math.matrix_zeros(3, 2)
        print("matrix2 =", matrix2)

        # Test creating a 1x1 matrix filled with zeros
        var matrix3: matrix[float] = stdlib.math.matrix_zeros(1, 1)
        print("matrix3 =", matrix3)
        """

        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ymr", delete=False) as f:
            f.write(script)
            temp_file = f.name

        try:
            # Capture output
            import io
            from contextlib import redirect_stdout

            f = io.StringIO()
            with redirect_stdout(f):
                self.interpreter.run_ymir_script(temp_file)

            output = f.getvalue()

            # Check that matrices were created with correct dimensions and values
            assert "matrix1 = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]" in output
            assert "matrix2 = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]" in output
            assert "matrix3 = [[0.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_ones(self):
        """Test matrix creation filled with ones."""
        script = """
        module test_matrix_ones

        import stdlib.math

        # Test creating a 2x3 matrix filled with ones
        var matrix1: matrix[float] = stdlib.math.matrix_ones(2, 3)
        print("matrix1 =", matrix1)

        # Test creating a 3x2 matrix filled with ones
        var matrix2: matrix[float] = stdlib.math.matrix_ones(3, 2)
        print("matrix2 =", matrix2)

        # Test creating a 1x1 matrix filled with ones
        var matrix3: matrix[float] = stdlib.math.matrix_ones(1, 1)
        print("matrix3 =", matrix3)
        """

        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ymr", delete=False) as f:
            f.write(script)
            temp_file = f.name

        try:
            # Capture output
            import io
            from contextlib import redirect_stdout

            f = io.StringIO()
            with redirect_stdout(f):
                self.interpreter.run_ymir_script(temp_file)

            output = f.getvalue()

            # Check that matrices were created with correct dimensions and values
            assert "matrix1 = [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]" in output
            assert "matrix2 = [[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]]" in output
            assert "matrix3 = [[1.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_eye(self):
        """Test identity matrix creation."""
        script = """
        module test_matrix_eye

        import stdlib.math

        # Test creating a 2x2 identity matrix
        var matrix1: matrix[float] = stdlib.math.matrix_eye(2)
        print("matrix1 =", matrix1)

        # Test creating a 3x3 identity matrix
        var matrix2: matrix[float] = stdlib.math.matrix_eye(3)
        print("matrix2 =", matrix2)

        # Test creating a 1x1 identity matrix
        var matrix3: matrix[float] = stdlib.math.matrix_eye(1)
        print("matrix3 =", matrix3)
        """

        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ymr", delete=False) as f:
            f.write(script)
            temp_file = f.name

        try:
            # Capture output
            import io
            from contextlib import redirect_stdout

            f = io.StringIO()
            with redirect_stdout(f):
                self.interpreter.run_ymir_script(temp_file)

            output = f.getvalue()

            # Check that identity matrices were created correctly
            assert "matrix1 = [[1.0, 0.0], [0.0, 1.0]]" in output
            assert "matrix2 = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]" in output
            assert "matrix3 = [[1.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_diag(self):
        """Test creating a diagonal matrix from a vector."""
        script = """
        module test_matrix_diag
        import stdlib.math

        var diag1: array[float] = [1.0, 2.0, 3.0]
        var matrix1: matrix[float] = stdlib.math.matrix_diag(diag1)
        print("matrix1 =", matrix1)

        var diag2: array[float] = [5.0]
        var matrix2: matrix[float] = stdlib.math.matrix_diag(diag2)
        print("matrix2 =", matrix2)
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ymr", delete=False) as f:
            f.write(script)
            temp_file = f.name
        try:
            import io
            from contextlib import redirect_stdout

            f = io.StringIO()
            with redirect_stdout(f):
                self.interpreter.run_ymir_script(temp_file)
            output = f.getvalue()
            assert "matrix1 = [[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 3.0]]" in output
            assert "matrix2 = [[5.0]]" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_flatten(self):
        """Test flattening a matrix to a 1D array."""
        script = """
        module test_matrix_flatten
        import stdlib.math

        var matrix1: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var flat1: array[float] = stdlib.math.matrix_flatten(matrix1)
        print("flat1 =", flat1)

        var matrix2: matrix[float] = [[5.0]]
        var flat2: array[float] = stdlib.math.matrix_flatten(matrix2)
        print("flat2 =", flat2)
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ymr", delete=False) as f:
            f.write(script)
            temp_file = f.name
        try:
            import io
            from contextlib import redirect_stdout

            f = io.StringIO()
            with redirect_stdout(f):
                self.interpreter.run_ymir_script(temp_file)
            output = f.getvalue()
            assert "flat1 = [1.0, 2.0, 3.0, 4.0]" in output
            assert "flat2 = [5.0]" in output
        finally:
            os.unlink(temp_file)
