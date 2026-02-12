def deeply_nested(x):
    """Function designed to trigger deep nesting smell in the analyzer."""
    result = 0

    # Level 1: first conditional
    if x > 0:
        # Level 2: for-loop inside the first if
        for i in range(5):
            # Level 3: nested if inside the for-loop
            if i % 2 == 0:
                # Level 4: while-loop inside the nested if
                while x > 0:
                    x -= 1
                    # Level 5: inner if inside the while-loop
                    if x % 3 == 0:
                        # Level 6: inner for-loop
                        for j in range(3):
                            # Level 7: innermost if
                            if j == 1:
                                # Some arbitrary computation
                                result += i + j + x

    return result
