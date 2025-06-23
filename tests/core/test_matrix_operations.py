import os
import tempfile

from ymir.core.lexer import Lexer
from ymir.core.parser import Parser
from ymir.interpreter import YmirInterpreter


class TestMatrixOperations:
    def setup_method(self):
        self.interpreter = YmirInterpreter(verbosity="WARNING")
        # Initialize parser for direct expression evaluation tests
        self.lexer = Lexer("", verbosity="WARNING")
        self.parser = Parser([], verbosity="WARNING")

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

    def test_matrix_sum(self):
        """Test matrix sum operations with different axes."""
        script = """
        module test_matrix_sum
        import stdlib.math

        var matrix1: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var sum_all: float = stdlib.math.matrix_sum(matrix1, -1)
        print("sum_all =", sum_all)

        var sum_cols: array[float] = stdlib.math.matrix_sum(matrix1, 0)
        print("sum_cols =", sum_cols)

        var sum_rows: array[float] = stdlib.math.matrix_sum(matrix1, 1)
        print("sum_rows =", sum_rows)
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
            assert "sum_all = 10.0" in output
            assert "sum_cols = [4.0, 6.0]" in output
            assert "sum_rows = [3.0, 7.0]" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_mean(self):
        """Test matrix mean operations with different axes."""
        script = """
        module test_matrix_mean
        import stdlib.math

        var matrix1: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var mean_all: float = stdlib.math.matrix_mean(matrix1, -1)
        print("mean_all =", mean_all)

        var mean_cols: array[float] = stdlib.math.matrix_mean(matrix1, 0)
        print("mean_cols =", mean_cols)

        var mean_rows: array[float] = stdlib.math.matrix_mean(matrix1, 1)
        print("mean_rows =", mean_rows)
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
            assert "mean_all = 2.5" in output
            assert "mean_cols = [2.0, 3.0]" in output
            assert "mean_rows = [1.5, 3.5]" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_var(self):
        """Test matrix variance operations with different axes."""
        script = """
        module test_matrix_var
        import stdlib.math

        var matrix1: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var var_all: float = stdlib.math.matrix_var(matrix1, -1)
        print("var_all =", var_all)

        var var_cols: array[float] = stdlib.math.matrix_var(matrix1, 0)
        print("var_cols =", var_cols)

        var var_rows: array[float] = stdlib.math.matrix_var(matrix1, 1)
        print("var_rows =", var_rows)
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
            # For matrix [[1,2],[3,4]], variance should be ~1.67
            assert "var_all =" in output
            assert "var_cols =" in output
            assert "var_rows =" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_std(self):
        """Test matrix standard deviation operations with different axes."""
        script = """
        module test_matrix_std
        import stdlib.math

        var matrix1: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var std_all: float = stdlib.math.matrix_std(matrix1, -1)
        print("std_all =", std_all)

        var std_cols: array[float] = stdlib.math.matrix_std(matrix1, 0)
        print("std_cols =", std_cols)

        var std_rows: array[float] = stdlib.math.matrix_std(matrix1, 1)
        print("std_rows =", std_rows)
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
            # For matrix [[1,2],[3,4]], std should be ~1.29
            assert "std_all =" in output
            assert "std_cols =" in output
            assert "std_rows =" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_min(self):
        """Test matrix minimum operations with different axes."""
        script = """
        module test_matrix_min
        import stdlib.math

        var matrix1: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var min_all: float = stdlib.math.matrix_min(matrix1, -1)
        print("min_all =", min_all)

        var min_cols: array[float] = stdlib.math.matrix_min(matrix1, 0)
        print("min_cols =", min_cols)

        var min_rows: array[float] = stdlib.math.matrix_min(matrix1, 1)
        print("min_rows =", min_rows)
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
            assert "min_all = 1.0" in output
            assert "min_cols = [1.0, 2.0]" in output
            assert "min_rows = [1.0, 3.0]" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_max(self):
        """Test matrix maximum operations with different axes."""
        script = """
        module test_matrix_max
        import stdlib.math

        var matrix1: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var max_all: float = stdlib.math.matrix_max(matrix1, -1)
        print("max_all =", max_all)

        var max_cols: array[float] = stdlib.math.matrix_max(matrix1, 0)
        print("max_cols =", max_cols)

        var max_rows: array[float] = stdlib.math.matrix_max(matrix1, 1)
        print("max_rows =", max_rows)
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
            assert "max_all = 4.0" in output
            assert "max_cols = [3.0, 4.0]" in output
            assert "max_rows = [2.0, 4.0]" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_argmin(self):
        """Test matrix argmin operations with different axes."""
        script = """
        module test_matrix_argmin
        import stdlib.math

        var matrix1: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var argmin_all: array[int] = stdlib.math.matrix_argmin(matrix1, -1)
        print("argmin_all =", argmin_all)

        var argmin_cols: array[int] = stdlib.math.matrix_argmin(matrix1, 0)
        print("argmin_cols =", argmin_cols)

        var argmin_rows: array[int] = stdlib.math.matrix_argmin(matrix1, 1)
        print("argmin_rows =", argmin_rows)
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
            assert "argmin_all = [0, 0]" in output
            assert "argmin_cols = [0, 0]" in output
            assert "argmin_rows = [0, 0]" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_argmax(self):
        """Test matrix argmax operations with different axes."""
        script = """
        module test_matrix_argmax
        import stdlib.math

        var matrix1: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var argmax_all: array[int] = stdlib.math.matrix_argmax(matrix1, -1)
        print("argmax_all =", argmax_all)

        var argmax_cols: array[int] = stdlib.math.matrix_argmax(matrix1, 0)
        print("argmax_cols =", argmax_cols)

        var argmax_rows: array[int] = stdlib.math.matrix_argmax(matrix1, 1)
        print("argmax_rows =", argmax_rows)
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
            assert "argmax_all = [1, 1]" in output
            assert "argmax_cols = [1, 1]" in output
            assert "argmax_rows = [1, 1]" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_rank(self):
        """Test matrix rank calculation."""
        script = """
        module test_matrix_rank
        import stdlib.math

        # Test full rank matrix
        var matrix1: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var rank1: int = stdlib.math.matrix_rank(matrix1)
        print("rank1 =", rank1)

        # Test rank-deficient matrix
        var matrix2: matrix[float] = [[1.0, 2.0], [2.0, 4.0]]
        var rank2: int = stdlib.math.matrix_rank(matrix2)
        print("rank2 =", rank2)
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
            assert "rank1 =" in output
            assert "rank2 =" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_eigenvalues(self):
        """Test matrix eigenvalues calculation."""
        script = """
        module test_matrix_eigenvalues
        import stdlib.math

        # Test 2x2 matrix with real eigenvalues
        var matrix1: matrix[float] = [[4.0, 1.0], [2.0, 3.0]]
        var eigenvalues1: array[float] = stdlib.math.matrix_eigenvalues(matrix1)
        print("eigenvalues1 =", eigenvalues1)

        # Test identity matrix
        var matrix2: matrix[float] = [[1.0, 0.0], [0.0, 1.0]]
        var eigenvalues2: array[float] = stdlib.math.matrix_eigenvalues(matrix2)
        print("eigenvalues2 =", eigenvalues2)
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
            assert "eigenvalues1 =" in output
            assert "eigenvalues2 =" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_eigenvectors(self):
        """Test matrix eigenvectors calculation."""
        script = """
        module test_matrix_eigenvectors
        import stdlib.math

        # Test 2x2 matrix
        var matrix1: matrix[float] = [[4.0, 1.0], [2.0, 3.0]]
        var eigenvectors1: matrix[float] = stdlib.math.matrix_eigenvectors(matrix1)
        print("eigenvectors1 =", eigenvectors1)

        # Test identity matrix
        var matrix2: matrix[float] = [[1.0, 0.0], [0.0, 1.0]]
        var eigenvectors2: matrix[float] = stdlib.math.matrix_eigenvectors(matrix2)
        print("eigenvectors2 =", eigenvectors2)
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
            assert "eigenvectors1 =" in output
            assert "eigenvectors2 =" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_svd(self):
        """Test matrix SVD calculation."""
        script = """
        module test_matrix_svd
        import stdlib.math

        # Test 2x2 matrix
        var matrix1: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var singular_values1: array[float] = stdlib.math.matrix_svd(matrix1)
        print("singular_values1 =", singular_values1)

        # Test identity matrix
        var matrix2: matrix[float] = [[1.0, 0.0], [0.0, 1.0]]
        var singular_values2: array[float] = stdlib.math.matrix_svd(matrix2)
        print("singular_values2 =", singular_values2)
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
            assert "singular_values1 =" in output
            assert "singular_values2 =" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_eigenvectors_enhanced(self):
        """Test enhanced matrix eigenvectors calculation with real computation."""
        script = """
        module test_matrix_eigenvectors_enhanced
        import stdlib.math

        # Test 2x2 matrix with real eigenvectors
        var matrix1: matrix[float] = [[4.0, 1.0], [2.0, 3.0]]
        var eigenvectors1: matrix[float] = stdlib.math.matrix_eigenvectors(matrix1)
        print("eigenvectors1 =", eigenvectors1)

        # Test identity matrix
        var matrix2: matrix[float] = [[1.0, 0.0], [0.0, 1.0]]
        var eigenvectors2: matrix[float] = stdlib.math.matrix_eigenvectors(matrix2)
        print("eigenvectors2 =", eigenvectors2)
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
            assert "eigenvectors1 =" in output
            assert "eigenvectors2 =" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_eigenvalues_3x3(self):
        """Test matrix eigenvalues calculation for 3x3 matrices."""
        script = """
        module test_matrix_eigenvalues_3x3
        import stdlib.math

        # Test 3x3 matrix
        var matrix1: matrix[float] = [[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 3.0]]
        var eigenvalues1: array[float] = stdlib.math.matrix_eigenvalues(matrix1)
        print("eigenvalues1 =", eigenvalues1)
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
            assert "eigenvalues1 =" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_svd_full(self):
        """Test full SVD decomposition."""
        script = """
        module test_matrix_svd_full
        import stdlib.math

        # Test 2x2 matrix
        var matrix1: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var svd_result: any = stdlib.math.matrix_svd_full(matrix1)
        print("svd_result =", svd_result)
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
            assert "svd_result =" in output
        finally:
            os.unlink(temp_file)

    def test_matrix_condition_number(self):
        """Test matrix condition number calculation."""
        script = """
        module test_matrix_condition_number
        import stdlib.math

        # Test with well-conditioned matrix
        var a: matrix[float] = [[1.0, 0.0], [0.0, 1.0]]
        var condition: float = stdlib.math.matrix_condition_number(a)
        print("condition =", condition)

        # Test with ill-conditioned matrix
        var b: matrix[float] = [[1.0, 1.0], [1.0, 1.0001]]
        var condition2: float = stdlib.math.matrix_condition_number(b)
        print("condition2 =", condition2)
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

            # Check that condition numbers were calculated correctly
            assert "condition = 1.0" in output or "condition = 1" in output
            # The ill-conditioned matrix should have a large condition number
            assert "condition2 =" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_slicing(self):
        """Test matrix slicing operations."""
        script = """
        module test_matrix_slicing
        import stdlib.math

        var a: matrix[float] = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]

        # Test basic slicing
        var slice_result: matrix[float] = stdlib.math.matrix_slice(a, 0, 1, 0, 1)
        print("slice_result =", slice_result)

        # Test row extraction
        var row: array[float] = stdlib.math.matrix_get_row(a, 1)
        print("row =", row)

        # Test column extraction
        var col: array[float] = stdlib.math.matrix_get_col(a, 1)
        print("col =", col)
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

            # Check that slicing operations work correctly
            assert "slice_result = [[1.0, 2.0], [4.0, 5.0]]" in output
            assert "row = [4.0, 5.0, 6.0]" in output
            assert "col = [2.0, 5.0, 8.0]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_reshaping(self):
        """Test matrix reshaping operations."""
        script = """
        module test_matrix_reshaping
        import stdlib.math

        var a: matrix[float] = [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]]

        # Test reshape
        var reshaped: matrix[float] = stdlib.math.matrix_reshape(a, 4, 2)
        print("reshaped =", reshaped)

        # Test transpose
        var transposed: matrix[float] = stdlib.math.matrix_transpose(a)
        print("transposed =", transposed)
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

            # Check that reshaping operations work correctly
            assert "reshaped = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]" in output
            assert "transposed = [[1.0, 5.0], [2.0, 6.0], [3.0, 7.0], [4.0, 8.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_flipping(self):
        """Test matrix flipping operations."""
        script = """
        module test_matrix_flipping
        import stdlib.math

        var a: matrix[float] = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]

        # Test horizontal flip
        var h_flipped: matrix[float] = stdlib.math.matrix_flip_horizontal(a)
        print("h_flipped =", h_flipped)

        # Test vertical flip
        var v_flipped: matrix[float] = stdlib.math.matrix_flip_vertical(a)
        print("v_flipped =", v_flipped)
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

            # Check that flipping operations work correctly
            assert "h_flipped = [[3.0, 2.0, 1.0], [6.0, 5.0, 4.0]]" in output
            assert "v_flipped = [[4.0, 5.0, 6.0], [1.0, 2.0, 3.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_stacking(self):
        """Test matrix stacking operations."""
        script = """
        module test_matrix_stacking
        import stdlib.math

        var a: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var b: matrix[float] = [[5.0, 6.0], [7.0, 8.0]]

        # Test vertical stacking
        var vstacked: matrix[float] = stdlib.math.matrix_vstack(a, b)
        print("vstacked =", vstacked)

        # Test horizontal stacking
        var hstacked: matrix[float] = stdlib.math.matrix_hstack(a, b)
        print("hstacked =", hstacked)
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

            # Check that stacking operations work correctly
            assert "vstacked = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]" in output
            assert "hstacked = [[1.0, 2.0, 5.0, 6.0], [3.0, 4.0, 7.0, 8.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_splitting(self):
        """Test matrix splitting operations."""
        script = """
        module test_matrix_splitting
        import stdlib.math

        var a: matrix[float] = [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0], [9.0, 10.0, 11.0, 12.0]]

        # Test vertical split
        var v_split: array[matrix[float]] = stdlib.math.matrix_vsplit(a, 3)
        print("v_split =", v_split)

        # Test horizontal split
        var h_split: array[matrix[float]] = stdlib.math.matrix_hsplit(a, 2)
        print("h_split =", h_split)
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

            # Check that splitting operations work correctly
            assert "v_split = [[[1.0, 2.0, 3.0, 4.0]], [[5.0, 6.0, 7.0, 8.0]], [[9.0, 10.0, 11.0, 12.0]]]" in output
            assert "h_split = [[[1.0, 2.0], [5.0, 6.0], [9.0, 10.0]], [[3.0, 4.0], [7.0, 8.0], [11.0, 12.0]]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_broadcasting(self):
        """Test matrix broadcasting operations."""
        script = """
        module test_matrix_broadcasting
        import stdlib.math

        var a: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var scalar: matrix[float] = [[5.0]]

        # Test broadcasting addition
        var broadcasted: matrix[float] = stdlib.math.matrix_broadcast_add(a, scalar)
        print("broadcasted =", broadcasted)
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

            # Check that broadcasting operations work correctly
            assert "broadcasted = [[6.0, 7.0], [8.0, 9.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_optimized_operations(self):
        """Test optimized matrix operations."""
        script = """
        module test_matrix_optimized_operations
        import stdlib.math

        var a: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var b: matrix[float] = [[5.0, 6.0], [7.0, 8.0]]

        # Test optimized multiplication
        var optimized_mult: matrix[float] = stdlib.math.matrix_optimized_multiply(a, b)
        print("optimized_mult =", optimized_mult)

        # Test chunked operations
        var chunked_sqrt: matrix[float] = stdlib.math.matrix_chunked_operation(a, 2, "sqrt")
        print("chunked_sqrt =", chunked_sqrt)
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

            # Check that optimized operations work correctly
            assert "optimized_mult = [[19.0, 22.0], [43.0, 50.0]]" in output
            assert "chunked_sqrt = [[1.0, 1.4142135623730951], [1.7320508075688772, 2.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_sparse_matrix_operations(self):
        """Test sparse matrix operations."""
        script = """
        module test_sparse_matrix_operations
        import stdlib.math

        var a: matrix[float] = [[1.0, 0.0, 3.0], [0.0, 5.0, 0.0], [7.0, 0.0, 9.0]]

        # Test conversion to sparse format
        var sparse_format: any = stdlib.math.matrix_to_sparse_format(a)
        print("sparse_format =", sparse_format)

        # Test conversion back to dense
        var back_to_dense: matrix[float] = stdlib.math.sparse_to_dense_matrix(sparse_format)
        print("back_to_dense =", back_to_dense)
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

            # Check that sparse operations work correctly
            assert "sparse_format = [[0, 0, 1, 2, 2], [0, 2, 1, 0, 2], [1.0, 3.0, 5.0, 7.0, 9.0], [3, 3]]" in output
            assert "back_to_dense = [[1.0, 0.0, 3.0], [0.0, 5.0, 0.0], [7.0, 0.0, 9.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_advanced_matrix_operations(self):
        """Test advanced matrix operations."""
        script = """
        module test_advanced_matrix_operations
        import stdlib.math

        var a: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var b: matrix[float] = [[5.0, 6.0], [7.0, 8.0]]

        # Test Kronecker product
        var kronecker: matrix[float] = stdlib.math.matrix_kronecker_product(a, b)
        print("kronecker =", kronecker)

        # Test Hadamard product
        var hadamard: matrix[float] = stdlib.math.matrix_hadamard_product(a, b)
        print("hadamard =", hadamard)

        # Test outer product
        var vec_a: array[float] = [1.0, 2.0]
        var vec_b: array[float] = [3.0, 4.0, 5.0]
        var outer: matrix[float] = stdlib.math.matrix_outer_product(vec_a, vec_b)
        print("outer =", outer)
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

            # Check that advanced operations work correctly
            assert (
                "kronecker = [[5.0, 6.0, 10.0, 12.0], [7.0, 8.0, 14.0, 16.0], [15.0, 18.0, 20.0, 24.0], [21.0, 24.0, 28.0, 32.0]]"  # noqa: E501
                in output
            )
            assert "hadamard = [[5.0, 12.0], [21.0, 32.0]]" in output
            assert "outer = [[3.0, 4.0, 5.0], [6.0, 8.0, 10.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_statistics(self):
        """Test matrix statistics operations."""
        script = """
        module test_matrix_statistics
        import stdlib.math

        var a: matrix[float] = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]

        # Test correlation matrix
        var correlation: matrix[float] = stdlib.math.matrix_correlation(a)
        print("correlation =", correlation)

        # Test covariance matrix
        var covariance: matrix[float] = stdlib.math.matrix_covariance(a)
        print("covariance =", covariance)
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

            # Check that statistics operations work correctly
            assert "correlation = [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]" in output
            assert "covariance = [[9.0, 9.0, 9.0], [9.0, 9.0, 9.0], [9.0, 9.0, 9.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_decompositions(self):
        """Test matrix decomposition operations."""
        script = """
        module test_matrix_decompositions
        import stdlib.math

        var a: matrix[float] = [[4.0, 12.0, -16.0], [12.0, 37.0, -43.0], [-16.0, -43.0, 98.0]]

        # Test Cholesky decomposition
        var cholesky: matrix[float] = stdlib.math.matrix_cholesky_decomposition(a)
        print("cholesky =", cholesky)
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

            # Check that decomposition works correctly
            assert "cholesky = [[2.0, 0.0, 0.0], [6.0, 1.0, 0.0], [-8.0, 5.0, 3.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_norms(self):
        """Test matrix norm calculations."""
        script = """
        module test_matrix_norms
        import stdlib.math

        var a: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]

        # Test Frobenius norm
        var frobenius: float = stdlib.math.matrix_frobenius_norm(a)
        print("frobenius =", frobenius)

        # Test L1 norm
        var l1_norm: float = stdlib.math.matrix_l1_norm(a)
        print("l1_norm =", l1_norm)

        # Test infinity norm
        var inf_norm: float = stdlib.math.matrix_infinity_norm(a)
        print("inf_norm =", inf_norm)
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

            # Check that norm calculations work correctly
            assert "frobenius = 5.477225575051661" in output
            assert "l1_norm = 6.0" in output
            assert "inf_norm = 7.0" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_distances(self):
        """Test matrix distance calculations."""
        script = """
        module test_matrix_distances
        import stdlib.math

        var a: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var b: matrix[float] = [[5.0, 6.0], [7.0, 8.0]]

        # Test Euclidean distance
        var euclidean: float = stdlib.math.matrix_euclidean_distance(a, b)
        print("euclidean =", euclidean)

        # Test Manhattan distance
        var manhattan: float = stdlib.math.matrix_manhattan_distance(a, b)
        print("manhattan =", manhattan)

        # Test cosine similarity
        var cosine: float = stdlib.math.matrix_cosine_similarity(a, b)
        print("cosine =", cosine)
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

            # Check that distance calculations work correctly
            assert "euclidean = 8.0" in output
            assert "manhattan = 16.0" in output
            assert "cosine = 0.9688639316269662" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_gpu_placeholder_functions(self):
        """Test GPU placeholder functions."""
        script = """
        module test_gpu_placeholder_functions
        import stdlib.math

        # Test GPU availability (should return false for now)
        var gpu_available: bool = stdlib.math.matrix_gpu_available()
        print("gpu_available =", gpu_available)

        # Test matrix to GPU transfer
        var matrix_x: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var gpu_matrix: any = stdlib.math.matrix_to_gpu(matrix_x)
        print("gpu_matrix =", gpu_matrix)
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

            # Check that GPU functions work correctly
            assert "gpu_available = False" in output
            assert "gpu_matrix = [[1.0, 2.0], [3.0, 4.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_set_operations(self):
        """Test matrix set operations."""
        script = """
        module test_matrix_set_operations
        import stdlib.math

        var a: matrix[float] = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]
        var new_row: array[float] = [10.0, 11.0, 12.0]
        var new_col: array[float] = [13.0, 14.0, 15.0]

        # Test set row
        var set_row_result: matrix[float] = stdlib.math.matrix_set_row(a, 1, new_row)
        print("set_row_result =", set_row_result)

        # Test set column
        var set_col_result: matrix[float] = stdlib.math.matrix_set_col(a, 1, new_col)
        print("set_col_result =", set_col_result)
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

            # Check that set operations work correctly
            assert "set_row_result = [[1.0, 2.0, 3.0], [10.0, 11.0, 12.0], [7.0, 8.0, 9.0]]" in output
            assert "set_col_result = [[1.0, 13.0, 3.0], [4.0, 14.0, 6.0], [7.0, 15.0, 9.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_matrix_concatenate(self):
        """Test matrix concatenation with multiple arrays."""
        script = """
        module test_matrix_concatenate
        import stdlib.math

        var a: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
        var b: matrix[float] = [[5.0, 6.0], [7.0, 8.0]]
        var c: matrix[float] = [[9.0, 10.0], [11.0, 12.0]]
        var arrays: array[matrix[float]] = [a, b, c]

        # Test vertical concatenation
        var v_concat: matrix[float] = stdlib.math.matrix_concatenate(arrays, 0)
        print("v_concat =", v_concat)
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

            # Check that concatenation works correctly
            assert "v_concat = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0], [9.0, 10.0], [11.0, 12.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_lu_decomposition(self):
        """Test LU decomposition."""
        script = """
        module test_lu_decomposition
        import stdlib.math

        var a: matrix[float] = [[2.0, 1.0, 1.0], [4.0, -6.0, 0.0], [-2.0, 7.0, 2.0]]

        var lu: any = stdlib.math.matrix_lu_decomposition(a)
        print("lu =", lu)
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

            # Check that LU decomposition works correctly
            assert "lu =" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_performance_optimizations(self):
        """Test performance optimization functions."""
        script = """
        module test_performance_optimizations
        import stdlib.math

        var a: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]

        # Test parallel sum (should work same as regular sum for now)
        var parallel_sum: float = stdlib.math.matrix_parallel_sum(a, -1)
        print("parallel_sum =", parallel_sum)
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

            # Check that performance optimizations work correctly
            assert "parallel_sum = 10.0" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)

    def test_sparse_matrix_multiply(self):
        """Test sparse matrix multiplication."""
        script = """
        module test_sparse_matrix_multiply
        import stdlib.math

        # Create a simple sparse matrix
        var dense_matrix: matrix[float] = [[1.0, 0.0, 3.0], [0.0, 5.0, 0.0], [7.0, 0.0, 9.0]]

        # Convert to sparse format
        var sparse_format: any = stdlib.math.matrix_to_sparse_format(dense_matrix)
        print("sparse_format =", sparse_format)

        # Convert back to dense
        var back_to_dense: matrix[float] = stdlib.math.sparse_to_dense_matrix(sparse_format)
        print("back_to_dense =", back_to_dense)
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

            # Check that sparse matrix operations work correctly
            assert "sparse_format =" in output
            assert "back_to_dense = [[1.0, 0.0, 3.0], [0.0, 5.0, 0.0], [7.0, 0.0, 9.0]]" in output
        finally:
            # Clean up temporary file
            os.unlink(temp_file)
