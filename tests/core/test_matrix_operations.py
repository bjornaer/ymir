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
