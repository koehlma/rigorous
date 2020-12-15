# It is an implementation detail that integers between -5 and 256
# always have the same identity. Fix: Use `==` instead of `is`.
#
# See: https://docs.python.org/3/c-api/long.html#c.PyLong_FromLong

try:
  x = iter.__class__.__call__(iter, (5,6))
  assert x.__next__() == 5  # fixed: originally '... is 5'
  assert x.__next__() == 6  # fixed: originally '... is 6'
  y = 8
  assert x.__next__() and False
except StopIteration as e:
  z = 9
  assert y == 8
  assert e.__context__ is None
assert z == 9
