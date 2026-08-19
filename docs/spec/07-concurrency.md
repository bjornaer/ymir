# 07 — Concurrency

Ymir's model is Go's: lightweight tasks communicating over typed channels. There is no
`async`/`await`, no futures, and no user-visible event loop.

The normative implementation hosts tasks on goroutines and channels on Go channels
(decision D4), so this chapter describes a model the host provides directly rather
than one emulated on top of something else.

*Legacy note:* the previous implementation ran tasks on a single-threaded asyncio
loop, so "concurrency" was cooperative interleaving under the GIL, never parallelism.
The model below is genuinely parallel.

## Tasks

```ymr
spawn worker(1, ch)
```

`spawn` evaluates the call's arguments **in the calling task, immediately**, then runs
the call in a new task. It is a statement and produces no value — there is no task
handle in v1.

A spawned call **MUST NOT** be passed a linear value (rule L5, chapter 02).

The program exits when `main` returns, **without** waiting for spawned tasks.
Coordinate with channels if you need to wait. *(Open: whether to add structured
concurrency — a scope that joins its tasks — instead of this. Go's choice here is
widely considered its worst concurrency decision.)*

## Channels

```ymr
ch := make_chan[int]()        # unbuffered (synchronous)
ch := make_chan[int](10)      # buffered, capacity 10
```

`chan[T]` is a typed conduit. Channels are reference values; the zero value is `nil`,
and any operation on a `nil` channel blocks forever.

### Send and receive

```ymr
ch <- 42            # send; statement
v := <-ch           # receive; expression of type T
v, ok := <-ch       # two-value receive; ok is false if the channel is closed and drained
```

An unbuffered send blocks until a receiver takes the value. A buffered send blocks
only when the buffer is full. A receive blocks until a value is available.

`<-` is always a single token (chapter 01), so `a<-b` is a send.

### Closing

```ymr
close(ch)
```

After close: further sends **panic**; receives drain the buffer, then yield the zero
value with `ok == false` forever. Closing an already-closed or `nil` channel panics.
Only the sending side should close a channel.

A closed channel is what makes `for v in ch` terminate:

```ymr
for v in ch {        # ranges until ch is closed and drained
    print(v)
}
```

## `select`

Waits on multiple channel operations; proceeds with whichever is ready.

```ymr
select {
    case v := <-in:      print("got " + str(v))
    case out <- x:       print("sent")
    case default:        print("nothing ready")
}
```

If several cases are ready, one is chosen **pseudo-randomly** — this is normative, to
prevent starvation and to stop programs depending on case order. With no `default` and
nothing ready, `select` blocks. With `default`, it never blocks.

## Memory model

A value sent on a channel **happens-before** the corresponding receive completes. This
is the only ordering guarantee Ymir provides, and channels are the only sanctioned
means of communication between tasks.

Ymir has no mutexes, atomics, or shared-memory primitives in v1. Two tasks holding
references to the same `array` or `map` and mutating them concurrently is a **data
race**, whose behavior is *unspecified*.

This is the one place v1 falls short of "no undefined behavior in safe code," and it
is a known hole. Options under consideration: a race detector in the VM (cheap for a
bytecode interpreter, unlike native code), or making `array`/`map` non-sendable so
sharing is impossible. **Open question, must be answered before Phase 5 of `/PLAN.md`.**

## Worked example

```ymr
module worker_pool

func worker(id: int, jobs: chan[int], results: chan[int]) {
    for j in jobs {
        results <- j * 2
    }
}

func main() {
    jobs := make_chan[int](100)
    results := make_chan[int](100)

    for w in range(1, 4) {
        spawn worker(w, jobs, results)
    }

    for j in range(1, 10) {
        jobs <- j
    }
    close(jobs)

    for a in range(1, 10) {
        print(str(<-results))
    }
}
```
