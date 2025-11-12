# Ymir Concurrency Guide

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

### Send Operation

Send a value to a channel using the `<-` operator:

```ymr
ch <- value
```

### Receive Operation

Receive a value from a channel:

```ymr
value <- ch
```

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
        value <- ch
        print("Received: " + str(value))
        i = i + 1
    }
}

func main() {
    ch = make_channel(5)
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
    value <- ch  # Will receive the value
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
    result = n * n
    result_ch <- result
}

func main() {
    ch = make_channel(5)
    
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
        result <- ch
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
        n <- in
        out <- (n * n)
        i = i + 1
    }
}

func print_results(in: any) {
    var i: int = 0
    while i < 10 {
        result <- in
        print("Result: " + str(result))
        i = i + 1
    }
}

func main() {
    ch1 = make_channel(5)
    ch2 = make_channel(5)
    
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
        job <- jobs
        result = job * 2
        results <- result
        print("Worker " + str(id) + " processed: " + str(job))
        i = i + 1
    }
}

func main() {
    jobs = make_channel(10)
    results = make_channel(10)
    
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
        result <- results
        print("Got result: " + str(result))
        j = j + 1
    }
}
```

## Implementation Details

### Backend

Ymir's concurrency is implemented using Python's `asyncio` for I/O-bound tasks and `concurrent.futures.ThreadPoolExecutor` for CPU-bound tasks.

### Channels

Channels are implemented using `asyncio.Queue` with type safety wrappers.

### Performance

- Spawned tasks have minimal overhead
- Channels are optimized for throughput
- Buffered channels reduce blocking

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

