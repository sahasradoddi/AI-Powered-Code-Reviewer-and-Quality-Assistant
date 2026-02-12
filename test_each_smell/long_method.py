def very_long_function(a, b):
    result = 0
    for i in range(10):
        result += a + b
    for j in range(10):
        result += a - b
    if result > 0:
        result += 1
    if result > 10:
        result += 2
    if result > 20:
        result += 3
    if result > 30:
        result += 4
    if result > 40:
        result += 5
    if result > 50:
        result += 6
    if result > 60:
        result += 7
    if result > 70:
        result += 8
    if result > 80:
        result += 9
    if result > 90:
        result += 10
    if result > 100:
        result += 11
    return result
