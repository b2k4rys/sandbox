
def fibonacci_iterative(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

# Example usage: Find the 7th Fibonacci number
print(fibonacci_iterative(10))  # Output: 13
