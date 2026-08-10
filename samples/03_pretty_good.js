// Returns the n-th Fibonacci number iteratively. O(n) time, O(1) space.
// Throws TypeError if n is not an integer, RangeError if n is negative.

function fibonacci(n) {
  if (!Number.isInteger(n)) {
    throw new TypeError(`n must be an integer, got ${n}`);
  }
  if (n < 0) {
    throw new RangeError(`n must be non-negative, got ${n}`);
  }

  if (n < 2) {
    return n;
  }

  let prev = 0;
  let curr = 1;
  for (let i = 2; i <= n; i++) {
    const next = prev + curr;
    prev = curr;
    curr = next;
  }
  return curr;
}

// Print the first 10 Fibonacci numbers.
function main() {
  const results = [];
  for (let i = 0; i < 10; i++) {
    results.push(fibonacci(i));
  }
  console.log(results.join(", "));
}

main();

module.exports = { fibonacci };
