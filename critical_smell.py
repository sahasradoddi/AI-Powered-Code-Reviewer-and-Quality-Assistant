def god_function(a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t):
    """CRITICAL: God Function - 20 params + massive logic"""
    result = a + b + c + d + e + f + g + h + i + j + k + l + m + n + o + p + q + r + s + t
    
    # High cyclomatic complexity
    if result > 100:
        if a > b and c > d:
            if e > f or g > h:
                for x in range(20):
                    for y in range(10):
                        print(f"Massive nested loops {x*y}")
    
    # Empty exception handler = SMELL
    try:
        risky = 1 / (a - b)
    except:
        pass
    
    return result * 42

class GodClass:
    """CRITICAL: 10+ methods = Large Class"""
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    def method4(self): pass
    def method5(self): pass
    def method6(self): pass
    def method7(self): pass
    def method8(self): pass
    def method9(self): pass
    def method10(self): pass
