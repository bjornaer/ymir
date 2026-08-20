"""
Tests for JAX matrix backend.
"""

import pytest

from ymir.core.matrix_backend import JAXBackend, NumpyBackend, get_backend


class TestMatrixBackend:
    """Test matrix backend selection."""

    def test_get_backend_returns_backend(self):
        """Test that get_backend returns a backend."""
        backend = get_backend()
        assert backend is not None

    def test_backend_has_required_methods(self):
        """Test backend has all required methods."""
        backend = get_backend()
        required_methods = [
            "is_gpu_available",
            "to_array",
            "to_list",
            "add",
            "subtract",
            "multiply",
            "matmul",
            "transpose",
            "inverse",
            "determinant",
            "shape",
        ]
        for method in required_methods:
            assert hasattr(backend, method)


class TestNumpyBackend:
    """Test NumPy backend."""

    def setup_method(self):
        """Setup test environment."""
        self.backend = NumpyBackend()

    def test_gpu_not_available(self):
        """Test NumPy backend reports no GPU."""
        assert not self.backend.is_gpu_available()

    def test_matrix_operations(self):
        """Test basic matrix operations."""
        data1 = [[1.0, 2.0], [3.0, 4.0]]
        data2 = [[5.0, 6.0], [7.0, 8.0]]

        arr1 = self.backend.to_array(data1)
        arr2 = self.backend.to_array(data2)

        # Addition
        result = self.backend.add(arr1, arr2)
        result_list = self.backend.to_list(result)
        assert result_list[0][0] == 6.0
        assert result_list[1][1] == 12.0

    def test_matrix_transpose(self):
        """Test matrix transpose."""
        data = [[1.0, 2.0], [3.0, 4.0]]
        arr = self.backend.to_array(data)

        result = self.backend.transpose(arr)
        result_list = self.backend.to_list(result)

        assert result_list[0][0] == 1.0
        assert result_list[0][1] == 3.0
        assert result_list[1][0] == 2.0
        assert result_list[1][1] == 4.0

    def test_matrix_shape(self):
        """Test getting matrix shape."""
        data = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        arr = self.backend.to_array(data)

        shape = self.backend.shape(arr)
        assert shape == [2, 3]

    def test_matrix_multiply(self):
        """Test matrix multiplication."""
        data1 = [[1.0, 2.0], [3.0, 4.0]]
        data2 = [[5.0, 6.0], [7.0, 8.0]]

        arr1 = self.backend.to_array(data1)
        arr2 = self.backend.to_array(data2)

        result = self.backend.matmul(arr1, arr2)
        result_list = self.backend.to_list(result)

        # Expected: [[19, 22], [43, 50]]
        assert result_list[0][0] == 19.0
        assert result_list[0][1] == 22.0
        assert result_list[1][0] == 43.0
        assert result_list[1][1] == 50.0


class TestJAXBackend:
    """Test JAX backend."""

    def test_jax_backend_initialization(self):
        """Test JAX backend can be initialized."""
        try:
            backend = JAXBackend()
            assert backend is not None
        except ImportError:
            pytest.skip("JAX not installed")

    def test_jax_gpu_detection(self):
        """Test GPU detection."""
        try:
            backend = JAXBackend()
            # Should return bool without error
            gpu_available = backend.is_gpu_available()
            assert isinstance(gpu_available, bool)
        except ImportError:
            pytest.skip("JAX not installed")

    def test_jax_matrix_operations(self):
        """Test JAX matrix operations."""
        try:
            backend = JAXBackend()

            data1 = [[1.0, 2.0], [3.0, 4.0]]
            data2 = [[5.0, 6.0], [7.0, 8.0]]

            arr1 = backend.to_array(data1)
            arr2 = backend.to_array(data2)

            # Addition
            result = backend.add(arr1, arr2)
            result_list = backend.to_list(result)
            assert result_list[0][0] == 6.0
        except ImportError:
            pytest.skip("JAX not installed")

    def test_jax_gpu_transfer(self):
        """Test GPU memory transfer."""
        try:
            backend = JAXBackend()
            data = [[1.0, 2.0], [3.0, 4.0]]
            arr = backend.to_array(data)

            # Transfer to GPU (should work even without GPU)
            gpu_arr = backend.to_gpu(arr)
            assert gpu_arr is not None

            # Transfer back to CPU
            cpu_arr = backend.to_cpu(gpu_arr)
            result = backend.to_list(cpu_arr)
            assert result == data
        except ImportError:
            pytest.skip("JAX not installed")


class TestBackendSwitching:
    """Test switching between backends."""

    def test_backend_consistency(self):
        """Test that different backends give same results."""
        data1 = [[1.0, 2.0], [3.0, 4.0]]
        data2 = [[5.0, 6.0], [7.0, 8.0]]

        numpy_backend = NumpyBackend()
        arr1_np = numpy_backend.to_array(data1)
        arr2_np = numpy_backend.to_array(data2)
        result_np = numpy_backend.matmul(arr1_np, arr2_np)
        result_np_list = numpy_backend.to_list(result_np)

        try:
            jax_backend = JAXBackend()
            arr1_jax = jax_backend.to_array(data1)
            arr2_jax = jax_backend.to_array(data2)
            result_jax = jax_backend.matmul(arr1_jax, arr2_jax)
            result_jax_list = jax_backend.to_list(result_jax)

            # Results should be approximately equal
            for i in range(len(result_np_list)):
                for j in range(len(result_np_list[i])):
                    assert abs(result_np_list[i][j] - result_jax_list[i][j]) < 1e-6
        except ImportError:
            pytest.skip("JAX not installed")
