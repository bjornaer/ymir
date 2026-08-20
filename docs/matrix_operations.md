# Ymir Matrix Operations Documentation

> **SUPERSEDED.** This document describes the frozen Python implementation in
> `/ymir-legacy-py/`, and contains claims that have since been disproved by direct
> execution. It is kept for history. The normative definition of Ymir is
> [`/docs/spec/`](spec/), and the migration plan is [`/PLAN.md`](../PLAN.md).

This document provides comprehensive documentation for the advanced matrix operations and utilities available in the Ymir standard library math module.

## Table of Contents

1. [Basic Matrix Creation](#basic-matrix-creation)
2. [Matrix Slicing and Indexing](#matrix-slicing-and-indexing)
3. [Matrix Reshaping and Transposition](#matrix-reshaping-and-transposition)
4. [Matrix Stacking and Concatenation](#matrix-stacking-and-concatenation)
5. [Matrix Splitting](#matrix-splitting)
6. [Matrix Broadcasting](#matrix-broadcasting)
7. [Performance Optimizations](#performance-optimizations)
8. [Sparse Matrix Operations](#sparse-matrix-operations)
9. [Advanced Matrix Operations](#advanced-matrix-operations)
10. [Matrix Statistics](#matrix-statistics)
11. [Matrix Decompositions](#matrix-decompositions)
12. [Matrix Norms and Distances](#matrix-norms-and-distances)
13. [GPU Acceleration](#gpu-acceleration)

## Basic Matrix Creation

### `matrix_create(rows: int, cols: int, value: float) -> matrix[float]`
Creates a matrix with specified dimensions filled with a constant value.

```ymir
var matrix_a: matrix[float] = stdlib.math.matrix_create(3, 3, 1.0)
# Result: [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]
```

### `matrix_eye(size: int) -> matrix[float]`
Creates an identity matrix of specified size.

```ymir
var identity: matrix[float] = stdlib.math.matrix_eye(3)
# Result: [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
```

### `matrix_zeros(rows: int, cols: int) -> matrix[float]`
Creates a matrix filled with zeros.

```ymir
var zeros: matrix[float] = stdlib.math.matrix_zeros(2, 3)
# Result: [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
```

### `matrix_create_banded(rows: int, cols: int, bandwidth: int, value: float) -> matrix[float]`
Creates a banded matrix with specified bandwidth.

```ymir
var banded: matrix[float] = stdlib.math.matrix_create_banded(4, 4, 1, 1.0)
# Result: [[1.0, 1.0, 0.0, 0.0], [1.0, 1.0, 1.0, 0.0], [0.0, 1.0, 1.0, 1.0], [0.0, 0.0, 1.0, 1.0]]
```

## Matrix Slicing and Indexing

### `matrix_slice(matrix: matrix[float], start_row: int, end_row: int, start_col: int, end_col: int) -> matrix[float]`
Extracts a submatrix from the specified range.

```ymir
var data: matrix[float] = [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0], [9.0, 10.0, 11.0, 12.0]]
var slice_result: matrix[float] = stdlib.math.matrix_slice(data, 0, 1, 0, 1)
# Result: [[1.0, 2.0], [5.0, 6.0]]
```

### `matrix_get_row(matrix: matrix[float], row_index: int) -> array[float]`
Extracts a specific row from the matrix.

```ymir
var row: array[float] = stdlib.math.matrix_get_row(data, 1)
# Result: [5.0, 6.0, 7.0, 8.0]
```

### `matrix_get_col(matrix: matrix[float], col_index: int) -> array[float]`
Extracts a specific column from the matrix.

```ymir
var col: array[float] = stdlib.math.matrix_get_col(data, 2)
# Result: [3.0, 7.0, 11.0]
```

## Matrix Reshaping and Transposition

### `matrix_reshape(matrix: matrix[float], new_rows: int, new_cols: int) -> matrix[float]`
Reshapes a matrix to new dimensions.

```ymir
var original: matrix[float] = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
var reshaped: matrix[float] = stdlib.math.matrix_reshape(original, 3, 2)
# Result: [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
```

### `matrix_transpose(matrix: matrix[float]) -> matrix[float]`
Transposes a matrix (swaps rows and columns).

```ymir
var transposed: matrix[float] = stdlib.math.matrix_transpose(original)
# Result: [[1.0, 4.0], [2.0, 5.0], [3.0, 6.0]]
```

### `matrix_flip_horizontal(matrix: matrix[float]) -> matrix[float]`
Flips a matrix horizontally.

```ymir
var h_flipped: matrix[float] = stdlib.math.matrix_flip_horizontal(original)
# Result: [[3.0, 2.0, 1.0], [6.0, 5.0, 4.0]]
```

### `matrix_flip_vertical(matrix: matrix[float]) -> matrix[float]`
Flips a matrix vertically.

```ymir
var v_flipped: matrix[float] = stdlib.math.matrix_flip_vertical(original)
# Result: [[4.0, 5.0, 6.0], [1.0, 2.0, 3.0]]
```

## Matrix Stacking and Concatenation

### `matrix_vstack(matrix1: matrix[float], matrix2: matrix[float]) -> matrix[float]`
Stacks matrices vertically (adds rows).

```ymir
var a: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
var b: matrix[float] = [[5.0, 6.0], [7.0, 8.0]]
var vstacked: matrix[float] = stdlib.math.matrix_vstack(a, b)
# Result: [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]
```

### `matrix_hstack(matrix1: matrix[float], matrix2: matrix[float]) -> matrix[float]`
Stacks matrices horizontally (adds columns).

```ymir
var hstacked: matrix[float] = stdlib.math.matrix_hstack(a, b)
# Result: [[1.0, 2.0, 5.0, 6.0], [3.0, 4.0, 7.0, 8.0]]
```

### `matrix_concatenate(matrices: array[matrix[float]], axis: int) -> matrix[float]`
Concatenates multiple matrices along the specified axis.

```ymir
var arrays: array[matrix[float]] = [a, b, c]
var concatenated: matrix[float] = stdlib.math.matrix_concatenate(arrays, 0)
```

## Matrix Splitting

### `matrix_vsplit(matrix: matrix[float], num_splits: int) -> array[matrix[float]]`
Splits a matrix vertically into the specified number of parts.

```ymir
var big_matrix: matrix[float] = [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0], [9.0, 10.0, 11.0, 12.0]]
var v_split: array[matrix[float]] = stdlib.math.matrix_vsplit(big_matrix, 3)
```

### `matrix_hsplit(matrix: matrix[float], num_splits: int) -> array[matrix[float]]`
Splits a matrix horizontally into the specified number of parts.

```ymir
var h_split: array[matrix[float]] = stdlib.math.matrix_hsplit(big_matrix, 2)
```

## Matrix Broadcasting

### `matrix_broadcast_add(matrix1: matrix[float], matrix2: matrix[float]) -> matrix[float]`
Performs element-wise addition with broadcasting.

```ymir
var matrix_2x2: matrix[float] = [[1.0, 2.0], [3.0, 4.0]]
var scalar: matrix[float] = [[5.0]]
var broadcasted: matrix[float] = stdlib.math.matrix_broadcast_add(matrix_2x2, scalar)
# Result: [[6.0, 7.0], [8.0, 9.0]]
```

## Performance Optimizations

### `matrix_optimized_multiply(matrix1: matrix[float], matrix2: matrix[float]) -> matrix[float]`
Performs optimized matrix multiplication using cache-friendly algorithms.

```ymir
var optimized_mult: matrix[float] = stdlib.math.matrix_optimized_multiply(matrix_1, matrix_2)
```

### `matrix_chunked_operation(matrix: matrix[float], chunk_size: int, operation: str) -> matrix[float]`
Performs operations on matrix chunks for better cache utilization.

```ymir
var chunked_sqrt: matrix[float] = stdlib.math.matrix_chunked_operation(matrix_1, 2, "sqrt")
```

### `matrix_parallel_multiply(matrix1: matrix[float], matrix2: matrix[float], num_threads: int) -> matrix[float]`
Performs parallel matrix multiplication using multiple threads.

```ymir
var parallel_result: matrix[float] = stdlib.math.matrix_parallel_multiply(a, b, 4)
```

## Sparse Matrix Operations

### `matrix_to_sparse_format(matrix: matrix[float]) -> any`
Converts a dense matrix to sparse format (CSR - Compressed Sparse Row).

```ymir
var dense_matrix: matrix[float] = [[1.0, 0.0, 3.0], [0.0, 5.0, 0.0], [7.0, 0.0, 9.0]]
var sparse_format: any = stdlib.math.matrix_to_sparse_format(dense_matrix)
```

### `sparse_to_dense_matrix(sparse_format: any) -> matrix[float]`
Converts sparse format back to dense matrix.

```ymir
var back_to_dense: matrix[float] = stdlib.math.sparse_to_dense_matrix(sparse_format)
```

### `sparse_matrix_multiply(sparse1: any, sparse2: any) -> any`
Performs multiplication between sparse matrices.

```ymir
var sparse_result: any = stdlib.math.sparse_matrix_multiply(sparse1, sparse2)
```

## Advanced Matrix Operations

### `matrix_kronecker_product(matrix1: matrix[float], matrix2: matrix[float]) -> matrix[float]`
Computes the Kronecker product of two matrices.

```ymir
var kronecker: matrix[float] = stdlib.math.matrix_kronecker_product(matrix_x, matrix_y)
```

### `matrix_hadamard_product(matrix1: matrix[float], matrix2: matrix[float]) -> matrix[float]`
Computes the Hadamard (element-wise) product of two matrices.

```ymir
var hadamard: matrix[float] = stdlib.math.matrix_hadamard_product(matrix_x, matrix_y)
```

### `matrix_outer_product(vector1: array[float], vector2: array[float]) -> matrix[float]`
Computes the outer product of two vectors.

```ymir
var vec1: array[float] = [1.0, 2.0]
var vec2: array[float] = [3.0, 4.0, 5.0]
var outer: matrix[float] = stdlib.math.matrix_outer_product(vec1, vec2)
# Result: [[3.0, 4.0, 5.0], [6.0, 8.0, 10.0]]
```

## Matrix Statistics

### `matrix_correlation(matrix: matrix[float]) -> matrix[float]`
Computes the correlation matrix.

```ymir
var correlation: matrix[float] = stdlib.math.matrix_correlation(stats_matrix)
```

### `matrix_covariance(matrix: matrix[float]) -> matrix[float]`
Computes the covariance matrix.

```ymir
var covariance: matrix[float] = stdlib.math.matrix_covariance(stats_matrix)
```

### `matrix_condition_number(matrix: matrix[float]) -> float`
Computes the condition number of a matrix.

```ymir
var condition: float = stdlib.math.matrix_condition_number(a)
```

## Matrix Decompositions

### `matrix_cholesky_decomposition(matrix: matrix[float]) -> matrix[float]`
Performs Cholesky decomposition on a symmetric positive definite matrix.

```ymir
var cholesky: matrix[float] = stdlib.math.matrix_cholesky_decomposition(decomp_matrix)
```

### `matrix_svd(matrix: matrix[float]) -> array[float]`
Computes the singular values of a matrix.

```ymir
var svd_result: array[float] = stdlib.math.matrix_svd(a)
```

## Matrix Norms and Distances

### `matrix_frobenius_norm(matrix: matrix[float]) -> float`
Computes the Frobenius norm of a matrix.

```ymir
var frobenius: float = stdlib.math.matrix_frobenius_norm(norm_matrix)
```

### `matrix_l1_norm(matrix: matrix[float]) -> float`
Computes the L1 norm of a matrix.

```ymir
var l1_norm: float = stdlib.math.matrix_l1_norm(norm_matrix)
```

### `matrix_infinity_norm(matrix: matrix[float]) -> float`
Computes the infinity norm of a matrix.

```ymir
var inf_norm: float = stdlib.math.matrix_infinity_norm(norm_matrix)
```

### `matrix_euclidean_distance(matrix1: matrix[float], matrix2: matrix[float]) -> float`
Computes the Euclidean distance between two matrices.

```ymir
var euclidean: float = stdlib.math.matrix_euclidean_distance(matrix_dist1, matrix_dist2)
```

### `matrix_manhattan_distance(matrix1: matrix[float], matrix2: matrix[float]) -> float`
Computes the Manhattan distance between two matrices.

```ymir
var manhattan: float = stdlib.math.matrix_manhattan_distance(matrix_dist1, matrix_dist2)
```

### `matrix_cosine_similarity(matrix1: matrix[float], matrix2: matrix[float]) -> float`
Computes the cosine similarity between two matrices.

```ymir
var cosine: float = stdlib.math.matrix_cosine_similarity(matrix_dist1, matrix_dist2)
```

## GPU Acceleration

### `matrix_gpu_available() -> bool`
Checks if GPU acceleration is available.

```ymir
var gpu_available: bool = stdlib.math.matrix_gpu_available()
```

### `matrix_to_gpu(matrix: matrix[float]) -> any`
Transfers a matrix to GPU memory.

```ymir
var gpu_matrix: any = stdlib.math.matrix_to_gpu(matrix_x)
```

### `matrix_from_gpu(gpu_matrix: any) -> matrix[float]`
Transfers a matrix from GPU memory back to CPU.

```ymir
var cpu_matrix: matrix[float] = stdlib.math.matrix_from_gpu(gpu_matrix)
```

## Performance Considerations

### Memory Efficiency
- Use sparse matrices for matrices with many zero elements
- Use banded matrices for structured sparse matrices
- Consider chunked operations for large matrices

### Computational Efficiency
- Use optimized multiplication for large matrices
- Leverage parallel computation for CPU-intensive operations
- Use GPU acceleration when available for very large matrices

### Algorithm Selection
- Choose appropriate decomposition methods based on matrix properties
- Use condition number to assess numerical stability
- Consider matrix norms for error analysis

## Examples

See the following example files for complete usage examples:
- `examples/matrix_operations_demo.ymr` - Comprehensive demonstration of all operations
- `examples/matrix_performance_benchmark.ymr` - Performance benchmarking examples

## Future Enhancements

Planned enhancements include:
- More advanced sparse matrix formats (CSC, COO)
- Additional matrix decompositions (QR, LU, Eigenvalue)
- More sophisticated GPU acceleration
- Distributed computing support
- Machine learning specific operations
