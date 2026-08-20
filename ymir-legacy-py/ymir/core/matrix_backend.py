"""
Matrix backend abstraction layer supporting JAX (with GPU) and NumPy (CPU fallback).

This module provides a unified interface for matrix operations with automatic
backend selection based on GPU availability.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, List, Union

import numpy as np

logger = logging.getLogger("ymir.matrix_backend")


class MatrixBackend(ABC):
    """Abstract base class for matrix computation backends."""

    @abstractmethod
    def is_gpu_available(self) -> bool:
        """Check if GPU acceleration is available."""
        pass

    @abstractmethod
    def to_array(self, data: List[List[float]]) -> Any:
        """Convert Python nested list to backend array."""
        pass

    @abstractmethod
    def to_list(self, array: Any) -> List[List[float]]:
        """Convert backend array to Python nested list."""
        pass

    @abstractmethod
    def to_gpu(self, array: Any) -> Any:
        """Transfer array to GPU memory."""
        pass

    @abstractmethod
    def to_cpu(self, array: Any) -> Any:
        """Transfer array to CPU memory."""
        pass

    @abstractmethod
    def add(self, a: Any, b: Any) -> Any:
        """Element-wise addition."""
        pass

    @abstractmethod
    def subtract(self, a: Any, b: Any) -> Any:
        """Element-wise subtraction."""
        pass

    @abstractmethod
    def multiply(self, a: Any, b: Any) -> Any:
        """Element-wise multiplication."""
        pass

    @abstractmethod
    def matmul(self, a: Any, b: Any) -> Any:
        """Matrix multiplication."""
        pass

    @abstractmethod
    def transpose(self, a: Any) -> Any:
        """Matrix transpose."""
        pass

    @abstractmethod
    def inverse(self, a: Any) -> Any:
        """Matrix inverse."""
        pass

    @abstractmethod
    def determinant(self, a: Any) -> float:
        """Matrix determinant."""
        pass

    @abstractmethod
    def shape(self, a: Any) -> List[int]:
        """Get matrix shape."""
        pass

    @abstractmethod
    def zeros(self, rows: int, cols: int) -> Any:
        """Create zero matrix."""
        pass

    @abstractmethod
    def ones(self, rows: int, cols: int) -> Any:
        """Create ones matrix."""
        pass

    @abstractmethod
    def eye(self, size: int) -> Any:
        """Create identity matrix."""
        pass

    @abstractmethod
    def dot(self, a: Any, b: Any) -> Any:
        """Dot product."""
        pass


class NumpyBackend(MatrixBackend):
    """NumPy-based matrix backend (CPU only)."""

    def __init__(self):
        logger.debug("Initializing NumPy backend (CPU)")

    def is_gpu_available(self) -> bool:
        return False

    def to_array(self, data: List[List[float]]) -> np.ndarray:
        return np.array(data, dtype=np.float64)

    def to_list(self, array: np.ndarray) -> List[List[float]]:
        return array.tolist()

    def to_gpu(self, array: np.ndarray) -> np.ndarray:
        logger.warning("NumPy backend does not support GPU, returning CPU array")
        return array

    def to_cpu(self, array: np.ndarray) -> np.ndarray:
        return array

    def add(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return a + b

    def subtract(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return a - b

    def multiply(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return a * b

    def matmul(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return a @ b

    def transpose(self, a: np.ndarray) -> np.ndarray:
        return a.T

    def inverse(self, a: np.ndarray) -> np.ndarray:
        return np.linalg.inv(a)

    def determinant(self, a: np.ndarray) -> float:
        return float(np.linalg.det(a))

    def shape(self, a: np.ndarray) -> List[int]:
        return list(a.shape)

    def zeros(self, rows: int, cols: int) -> np.ndarray:
        return np.zeros((rows, cols), dtype=np.float64)

    def ones(self, rows: int, cols: int) -> np.ndarray:
        return np.ones((rows, cols), dtype=np.float64)

    def eye(self, size: int) -> np.ndarray:
        return np.eye(size, dtype=np.float64)

    def dot(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return np.dot(a, b)


class JAXBackend(MatrixBackend):
    """JAX-based matrix backend with GPU support."""

    def __init__(self):
        try:
            import jax
            import jax.numpy as jnp

            self.jax = jax
            self.jnp = jnp

            # Check for GPU availability
            self._gpu_available = False
            try:
                devices = jax.devices("gpu")
                if devices:
                    self._gpu_available = True
                    logger.debug(f"JAX backend initialized with GPU support: {devices}")
                else:
                    logger.debug("JAX backend initialized (CPU only - no GPU devices found)")
            except RuntimeError:
                logger.debug("JAX backend initialized (CPU only - GPU runtime not available)")

        except ImportError as e:
            raise ImportError("JAX is not installed. Install it with: pip install jax jaxlib") from e

    def is_gpu_available(self) -> bool:
        return self._gpu_available

    def to_array(self, data: List[List[float]]) -> Any:
        return self.jnp.array(data, dtype=self.jnp.float64)

    def to_list(self, array: Any) -> List[List[float]]:
        # Convert JAX array to numpy then to list
        return np.array(array).tolist()

    def to_gpu(self, array: Any) -> Any:
        """Transfer array to GPU memory."""
        if not self._gpu_available:
            logger.warning("No GPU available, array remains on CPU")
            return array

        try:
            # Use jax.device_put to move to GPU
            gpu_device = self.jax.devices("gpu")[0]
            return self.jax.device_put(array, gpu_device)
        except Exception as e:
            logger.error(f"Failed to transfer to GPU: {e}")
            return array

    def to_cpu(self, array: Any) -> Any:
        """Transfer array to CPU memory."""
        try:
            cpu_device = self.jax.devices("cpu")[0]
            return self.jax.device_put(array, cpu_device)
        except Exception as e:
            logger.error(f"Failed to transfer to CPU: {e}")
            return array

    def add(self, a: Any, b: Any) -> Any:
        return a + b

    def subtract(self, a: Any, b: Any) -> Any:
        return a - b

    def multiply(self, a: Any, b: Any) -> Any:
        return a * b

    def matmul(self, a: Any, b: Any) -> Any:
        return self.jnp.matmul(a, b)

    def transpose(self, a: Any) -> Any:
        return a.T

    def inverse(self, a: Any) -> Any:
        return self.jnp.linalg.inv(a)

    def determinant(self, a: Any) -> float:
        return float(self.jnp.linalg.det(a))

    def shape(self, a: Any) -> List[int]:
        return list(a.shape)

    def zeros(self, rows: int, cols: int) -> Any:
        return self.jnp.zeros((rows, cols), dtype=self.jnp.float64)

    def ones(self, rows: int, cols: int) -> Any:
        return self.jnp.ones((rows, cols), dtype=self.jnp.float64)

    def eye(self, size: int) -> Any:
        return self.jnp.eye(size, dtype=self.jnp.float64)

    def dot(self, a: Any, b: Any) -> Any:
        return self.jnp.dot(a, b)


def get_matrix_backend(prefer_jax: bool = True) -> MatrixBackend:
    """
    Get the best available matrix backend.

    Args:
        prefer_jax: If True, try to use JAX backend first, fall back to NumPy

    Returns:
        MatrixBackend instance
    """
    if prefer_jax:
        try:
            backend = JAXBackend()
            logger.debug("Using JAX backend for matrix operations")
            return backend
        except ImportError:
            logger.debug("JAX not available, falling back to NumPy backend")

    backend = NumpyBackend()
    logger.debug("Using NumPy backend for matrix operations")
    return backend


# Global backend instance
_backend: Union[MatrixBackend, None] = None


def get_backend() -> MatrixBackend:
    """Get or create the global matrix backend instance."""
    global _backend
    if _backend is None:
        _backend = get_matrix_backend(prefer_jax=True)
    return _backend


def set_backend(backend: MatrixBackend) -> None:
    """Set the global matrix backend instance."""
    global _backend
    _backend = backend
