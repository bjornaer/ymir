# Ymir Standard Library Reference

> **SUPERSEDED.** This document describes the frozen Python implementation in
> `/ymir-legacy-py/`, and contains claims that have since been disproved by direct
> execution. It is kept for history. The normative definition of Ymir is
> [`/docs/spec/`](spec/), and the migration plan is [`/PLAN.md`](../PLAN.md).

Complete reference for Ymir's standard library, including string methods, collection methods, and operators.

## Table of Contents

- [String Methods](#string-methods)
- [Collection Methods](#collection-methods)
- [Operators](#operators)
- [Best Practices](#best-practices)

---

## String Methods

All string methods in Ymir follow Python conventions and can be called directly on string values.

### Basic Transformations

#### `.upper() -> string`
Convert string to uppercase.

```ymir
s = "hello world"
result = s.upper()  // "HELLO WORLD"
```

#### `.lower() -> string`
Convert string to lowercase.

```ymir
s = "HELLO WORLD"
result = s.lower()  // "hello world"
```

#### `.capitalize() -> string`
Capitalize the first character.

```ymir
s = "hello world"
result = s.capitalize()  // "Hello world"
```

#### `.title() -> string`
Convert to title case (capitalize each word).

```ymir
s = "hello world"
result = s.title()  // "Hello World"
```

#### `.strip([chars]) -> string`
Remove leading and trailing whitespace (or specified characters).

```ymir
s = "  hello  "
result = s.strip()  // "hello"
```

#### `.lstrip([chars]) -> string`
Remove leading whitespace.

#### `.rstrip([chars]) -> string`
Remove trailing whitespace.

### Search and Check Methods

#### `.startswith(prefix, [start], [end]) -> bool`
Check if string starts with prefix.

```ymir
s = "hello world"
result = s.startswith("hello")  // true
```

#### `.endswith(suffix, [start], [end]) -> bool`
Check if string ends with suffix.

```ymir
s = "hello world"
result = s.endswith("world")  // true
```

#### `.find(sub, [start], [end]) -> int`
Find first occurrence of substring. Returns -1 if not found.

```ymir
s = "hello world"
result = s.find("world")  // 6
```

#### `.rfind(sub, [start], [end]) -> int`
Find last occurrence of substring.

#### `.index(sub, [start], [end]) -> int`
Like `find()` but raises error if not found.

#### `.count(sub, [start], [end]) -> int`
Count occurrences of substring.

```ymir
s = "hello world hello"
result = s.count("hello")  // 2
```

#### `.contains(sub) -> bool`
Check if substring exists in string.

```ymir
s = "hello world"
result = s.contains("world")  // true
```

### Manipulation Methods

#### `.split([sep], [maxsplit]) -> array[string]`
Split string into array.

```ymir
s = "hello,world,test"
result = s.split(",")  // ["hello", "world", "test"]

// Split on whitespace
s = "hello world"
result = s.split()  // ["hello", "world"]
```

#### `.replace(old, new, [count]) -> string`
Replace occurrences of substring.

```ymir
s = "hello world"
result = s.replace("world", "universe")  // "hello universe"
```

#### `.join(iterable) -> string`
Join array elements with string as separator.

```ymir
sep = ", "
arr = ["apple", "banana", "orange"]
result = sep.join(arr)  // "apple, banana, orange"
```

#### `.format(*args) -> string`
Format string with arguments (Python style).

```ymir
s = "Hello {}, you are {} years old"
result = s.format("John", 25)
```

### Validation Methods

#### `.isdigit() -> bool`
Check if all characters are digits.

```ymir
s = "12345"
result = s.isdigit()  // true
```

#### `.isalpha() -> bool`
Check if all characters are alphabetic.

```ymir
s = "hello"
result = s.isalpha()  // true
```

#### `.isalnum() -> bool`
Check if all characters are alphanumeric.

```ymir
s = "hello123"
result = s.isalnum()  // true
```

#### `.isspace() -> bool`
Check if all characters are whitespace.

#### `.isupper() -> bool`
Check if all characters are uppercase.

#### `.islower() -> bool`
Check if all characters are lowercase.

### Utility Methods

#### `.repeat(n) -> string`
Repeat string n times.

```ymir
s = "abc"
result = s.repeat(3)  // "abcabcabc"
```

#### `.reverse() -> string`
Reverse the string.

```ymir
s = "hello"
result = s.reverse()  // "olleh"
```

#### `.slice(start, [end]) -> string`
Extract substring.

```ymir
s = "hello world"
result = s.slice(0, 5)  // "hello"
```

---

## Collection Methods

All collection methods are immutable - they return new arrays without modifying the original.

### Aggregation Methods

#### `.sum() -> number`
Sum all numeric elements.

```ymir
arr = [1, 2, 3, 4, 5]
result = arr.sum()  // 15
```

#### `.min() -> any`
Find minimum element.

```ymir
arr = [5, 2, 8, 1, 9]
result = arr.min()  // 1
```

#### `.max() -> any`
Find maximum element.

```ymir
arr = [5, 2, 8, 1, 9]
result = arr.max()  // 9
```

#### `.avg() -> float` / `.mean() -> float`
Calculate average of numeric elements.

```ymir
arr = [2, 4, 6, 8]
result = arr.avg()  // 5.0
```

### Functional Programming Methods

#### `.filter(predicate) -> array`
Filter elements by predicate function.

```ymir
func isEven(n: int) -> bool {
    return n % 2 == 0
}

arr = [1, 2, 3, 4, 5, 6]
result = arr.filter(isEven)  // [2, 4, 6]
```

#### `.map(func) -> array`
Transform each element.

```ymir
func double(n: int) -> int {
    return n * 2
}

arr = [1, 2, 3, 4, 5]
result = arr.map(double)  // [2, 4, 6, 8, 10]
```

#### `.reduce(func, [initial]) -> any`
Reduce array to single value.

```ymir
func add(a: int, b: int) -> int {
    return a + b
}

arr = [1, 2, 3, 4, 5]
result = arr.reduce(add)  // 15
```

#### `.forEach(func) -> void`
Execute function for each element (side effects).

```ymir
func printItem(item: any) {
    print(str(item))
}

arr = [1, 2, 3]
arr.forEach(printItem)
```

### Utility Methods

#### `.sort() -> array`
Return sorted copy (ascending).

```ymir
arr = [5, 2, 8, 1, 9]
result = arr.sort()  // [1, 2, 5, 8, 9]
```

#### `.sortDesc() -> array`
Return sorted copy (descending).

```ymir
arr = [5, 2, 8, 1, 9]
result = arr.sortDesc()  // [9, 8, 5, 2, 1]
```

#### `.reverse() -> array`
Return reversed copy.

```ymir
arr = [1, 2, 3, 4, 5]
result = arr.reverse()  // [5, 4, 3, 2, 1]
```

#### `.slice(start, [end]) -> array`
Extract sub-array.

```ymir
arr = [1, 2, 3, 4, 5]
result = arr.slice(1, 4)  // [2, 3, 4]
```

#### `.indexOf(value) -> int`
Find first index of value. Returns -1 if not found.

```ymir
arr = [10, 20, 30, 40]
result = arr.indexOf(30)  // 2
```

#### `.lastIndexOf(value) -> int`
Find last index of value.

```ymir
arr = [1, 2, 3, 2, 1]
result = arr.lastIndexOf(2)  // 3
```

#### `.contains(value) -> bool`
Check if value exists in array.

```ymir
arr = [1, 2, 3, 4, 5]
result = arr.contains(3)  // true
```

#### `.unique() -> array`
Return array with duplicates removed (order preserved).

```ymir
arr = [1, 2, 2, 3, 1, 4]
result = arr.unique()  // [1, 2, 3, 4]
```

#### `.flatten() -> array`
Flatten nested arrays (one level).

```ymir
arr = [[1, 2], [3, 4], [5, 6]]
result = arr.flatten()  // [1, 2, 3, 4, 5, 6]
```

#### `.join(separator) -> string`
Join elements as string.

```ymir
arr = [1, 2, 3, 4, 5]
result = arr.join(", ")  // "1, 2, 3, 4, 5"
```

### Existing Methods

#### `.append(value) -> array`
Return new array with value appended.

```ymir
arr = [1, 2, 3]
result = arr.append(4)  // [1, 2, 3, 4]
```

#### `.extend(other) -> array`
Return new array with other array concatenated.

```ymir
arr1 = [1, 2, 3]
arr2 = [4, 5, 6]
result = arr1.extend(arr2)  // [1, 2, 3, 4, 5, 6]
```

---

## Operators

### Addition (`+`)

**Numbers**: Arithmetic addition
```ymir
result = 5 + 3  // 8
```

**Strings**: Concatenation
```ymir
result = "hello" + " " + "world"  // "hello world"
```

**String + Number**: Automatic conversion
```ymir
result = "Count: " + 42  // "Count: 42"
result = 42 + " items"   // "42 items"
```

**Arrays**: Concatenation
```ymir
result = [1, 2] + [3, 4]  // [1, 2, 3, 4]
```

**Matrices**: Element-wise addition
```ymir
a = [[1, 2], [3, 4]]
b = [[5, 6], [7, 8]]
result = a + b  // [[6, 8], [10, 12]]
```

### Multiplication (`*`)

**Numbers**: Arithmetic multiplication
```ymir
result = 5 * 3  // 15
```

**String Repetition**: String * int or int * string
```ymir
result = "abc" * 3  // "abcabcabc"
result = 2 * "hello"  // "hellohello"
```

**Matrices**: Element-wise multiplication
```ymir
a = [[1, 2], [3, 4]]
b = [[2, 2], [2, 2]]
result = a * b  // [[2, 4], [6, 8]]
```

### Matrix Multiplication (`@`)

**Matrices**: Matrix multiplication
```ymir
a = [[1, 2], [3, 4]]
b = [[5, 6], [7, 8]]
result = a @ b  // [[19, 22], [43, 50]]
```

---

## Best Practices

### Immutability

All collection methods return new arrays:

```ymir
original = [3, 1, 2]
sorted_copy = original.sort()

// original is still [3, 1, 2]
// sorted_copy is [1, 2, 3]
```

### Method Chaining

Chain methods for clean, readable code:

```ymir
// String chaining
result = text.strip().lower().capitalize()

// Array chaining
result = data.unique().sort().slice(0, 10)
```

### Type Safety

Be aware of type requirements:

```ymir
// sum() requires numeric elements
numbers = [1, 2, 3]
total = numbers.sum()  // OK

mixed = [1, "two", 3]
total = mixed.sum()  // ERROR: non-numeric elements
```

### Empty Collections

Handle empty collections appropriately:

```ymir
arr = []

// These are safe
reversed = arr.reverse()  // []
unique = arr.unique()     // []

// These will error
minimum = arr.min()  // ERROR: empty sequence
maximum = arr.max()  // ERROR: empty sequence
average = arr.avg()  // ERROR: empty sequence
```

### Functional Programming

Use filter, map, and reduce for elegant data transformations:

```ymir
// Filter even numbers, double them, and sum
func isEven(n: int) -> bool { return n % 2 == 0 }
func double(n: int) -> int { return n * 2 }
func add(a: int, b: int) -> int { return a + b }

numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
result = numbers.filter(isEven).map(double).reduce(add)
// Result: 60 (2+4+6+8+10 doubled = 4+8+12+16+20)
```

### String Formatting

Prefer string methods over manual concatenation:

```ymir
// Good: Using methods
words = text.split(" ")
result = " | ".join(words)

// Less efficient: Manual loops
```

### Performance

- Use built-in methods when possible (they're optimized)
- Chain operations to avoid creating intermediate arrays
- For large datasets, consider using matrix operations

---

## Examples

See `examples/stdlib_showcase.ymr` for comprehensive examples of all standard library features.

