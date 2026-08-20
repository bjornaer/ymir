# Ymir Concurrency Guide

> **SUPERSEDED.** This document describes the frozen Python implementation in
> `/ymir-legacy-py/`, and contains claims that have since been disproved by direct
> execution. It is kept for history. The normative definition of Ymir is
> [`/docs/spec/`](spec/), and the migration plan is [`/PLAN.md`](../PLAN.md).

Ymir provides Go-style concurrency primitives that make parallel programming intuitive and safe.

## Table of Contents

1. [Spawning Tasks](#spawning-tasks)
2. [Channels](#channels)
3. [Channel Operations](#channel-operations)
4. [Best Practices](#best-practices)
5. [Examples](#examples)

## Spawning Tasks

Use the `spawn` keyword to launch a concurrent task. Spawned tasks run independently and can communicate via channels.

### Syntax

```ymr
spawn functionCall(args)
```

### Example

```ymr
func worker(id: int) {
    print("Worker " + str(id) + " running")
}

func main() {
    spawn worker(1)
    spawn worker(2)
    spawn worker(3)
}
```

Note: All functions are regular functions (no `async` keyword). Spawn works with any function.

## Channels

Channels provide type-safe communication between concurrent tasks. They can be buffered or unbuffered.

### Creating Channels

```ymr
# Unbuffered channel (blocking)
ch = make_channel(0)

# Buffered channel with capacity 10
ch = make_channel(10)
```

### Channel Types

Channels in Ymir can be declared with type annotations:

```ymr
var ch: chan[int]  # Channel of integers
var msg_ch: chan[string]  # Channel of strings
```

## Channel Operations

Ymir uses **Go-style channel syntax** to avoid ambiguity between send and receive operations.

### Send Operation

Send a value to a channel using the `<-` operator:

```ymr
ch <- value
```

### Receive Operation

Receive a value from a channel using the `:=` walrus operator with type annotation (for new variables) or `=` (for existing variables):

```ymr
# Receive and declare new variable with walrus operator
value: int := <-ch

# Receive into existing variable
value = <-ch
```

**Note**: The walrus operator `:=` requires a type annotation. The receive operation uses `<-ch` as a unary operator on the *right* side, with `:=` or `=` for assignment.

### Example with Send and Receive

```ymr
func producer(ch: any) {
    var i: int = 0
    while i < 5 {
        ch <- i
        i = i + 1
    }
}

func consumer(ch: any) {
    var i: int = 0
    while i < 5 {
        value: int := <-ch
        print("Received: " + str(value))
        i = i + 1
    }
}

func main() {
    var ch: any = make_channel(5)
    spawn producer(ch)
    consumer(ch)  # Run consumer in main task
}
```

## Best Practices

### 1. Always Close Channels When Done

Although Ymir doesn't currently have explicit channel closing, ensure your tasks complete properly.

### 2. Avoid Deadlocks

Make sure sends and receives are balanced:

```ymr
# Good: balanced sends and receives
func main() {
    ch = make_channel(1)
    ch <- 42
    value := <-ch  # Will receive the value
}

# Bad: will deadlock
func bad_example() {
    ch = make_channel(0)  # Unbuffered
    ch <- 42  # Blocks forever - no receiver!
}
```

### 3. Use Buffered Channels for Non-Blocking Sends

```ymr
# Buffered channel allows sends without immediate receiver
ch = make_channel(10)
var i: int = 0
while i < 10 {
    ch <- i  # Won't block
    i = i + 1
}
```

### 4. Error Handling in Concurrent Tasks

Wrap task logic in try-except blocks:

```ymr
func safe_worker(id: int, ch: any) {
    try {
        # Do work
        result = compute(id)
        ch <- result
    } except Exception as e {
        print("Worker " + str(id) + " failed: " + str(e))
        ch <- nil  # Send error indicator
    }
}
```

## Examples

### Example 1: Parallel Computation

```ymr
module parallel_computation

func compute_square(n: int, result_ch: any) {
    var result: int = n * n
    result_ch <- result
}

func main() {
    var ch: any = make_channel(5)
    
    # Spawn 5 workers
    var i: int = 0
    while i < 5 {
        spawn compute_square(i, ch)
        i = i + 1
    }
    
    # Collect results
    var j: int = 0
    var total: int = 0
    while j < 5 {
        result: int := <-ch
        total = total + result
        j = j + 1
    }
    
    print("Sum of squares: " + str(total))
}
```

### Example 2: Pipeline Pattern

```ymr
module pipeline

func generate_numbers(out: any) {
    var i: int = 0
    while i < 10 {
        out <- i
        i = i + 1
    }
}

func square(in: any, out: any) {
    var i: int = 0
    while i < 10 {
        n: int := <-in
        out <- (n * n)
        i = i + 1
    }
}

func print_results(in: any) {
    var i: int = 0
    while i < 10 {
        result: int := <-in
        print("Result: " + str(result))
        i = i + 1
    }
}

func main() {
    var ch1: any = make_channel(5)
    var ch2: any = make_channel(5)
    
    spawn generate_numbers(ch1)
    spawn square(ch1, ch2)
    print_results(ch2)
}
```

### Example 3: Fan-Out / Fan-In

```ymr
module fan_out_in

func worker(id: int, jobs: any, results: any) {
    var i: int = 0
    while i < 3 {
        job: int := <-jobs
        var result: int = job * 2
        results <- result
        print("Worker " + str(id) + " processed: " + str(job))
        i = i + 1
    }
}

func main() {
    var jobs: any = make_channel(10)
    var results: any = make_channel(10)
    
    # Start 3 workers (fan-out)
    spawn worker(1, jobs, results)
    spawn worker(2, jobs, results)
    spawn worker(3, jobs, results)
    
    # Send jobs
    var i: int = 0
    while i < 9 {
        jobs <- i
        i = i + 1
    }
    
    # Collect results (fan-in)
    var j: int = 0
    while j < 9 {
        result: int := <-results
        print("Got result: " + str(result))
        j = j + 1
    }
}
```

## Implementation Details

### Concurrency Runtime

Ymir uses a `ConcurrencyRuntime` that manages:
- Event loop (via Python's `asyncio` internally)
- Spawned tasks
- Channel operations
- Context tracking for spawned tasks

### Backend

- **Internal async**: Python's `asyncio` used internally for non-blocking I/O
- **Channels**: `asyncio.Queue` with type safety wrappers  
- **Event loop**: Automatically initialized and managed
- **User API**: Pure Go-style (spawn + channels), no async/await exposed

### Key Features

- **Go-style concurrency**: Only `spawn` and channels, no async/await keywords
- **Automatic event loop**: Event loop starts on first spawn/channel operation
- **Type safety**: Channels support type annotations
- **Transparent blocking**: Channel operations block from user perspective, async internally
- **No manual management**: Event loop lifecycle is automatic

### Performance

- Spawned tasks have minimal overhead
- Channels are optimized for throughput
- Buffered channels reduce blocking
- Internal async implementation ensures non-blocking I/O

## Future Enhancements

The following features are planned for future releases:

- `select` statement for multiplexing channels
- Explicit channel closing
- Timeout operations
- Context cancellation
- Worker pools

## See Also

- [Syntax Guidelines](syntax_guidelines.md)
- [HTTP Server Guide](http_server.md)
- [Matrix Operations](matrix_operations.md)

