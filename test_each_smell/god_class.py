class MegaProcessor:
    def __init__(self, data):
        self.data = data

    def step1(self):
        total = 0
        for item in self.data:
            total += item
        return total

    def step2(self):
        result = []
        for item in self.data:
            if item % 2 == 0:
                result.append(item * 2)
        return result

    def step3(self):
        count = 0
        for item in self.data:
            if item > 10:
                count += 1
        return count

    def step4(self):
        return [x for x in self.data if x < 0]

    def step5(self):
        s = set()
        for x in self.data:
            s.add(x % 5)
        return s

    def step6(self):
        d = {}
        for x in self.data:
            d[x] = x * x
        return d

    def step7(self):
        return sum(self.data) / (len(self.data) or 1)

    def step8(self):
        result = []
        for i, x in enumerate(self.data):
            result.append((i, x))
        return result

    def step9(self):
        acc = 1
        for x in self.data:
            acc *= (x or 1)
        return acc

    def step10(self):
        return sorted(self.data)

    def step11(self):
        result = []
        for x in self.data:
            if x % 3 == 0:
                result.append(x // 3)
        return result

    def run_all(self):
        return {
            "step1": self.step1(),
            "step2": self.step2(),
            "step3": self.step3(),
            "step4": self.step4(),
            "step5": self.step5(),
            "step6": self.step6(),
            "step7": self.step7(),
            "step8": self.step8(),
            "step9": self.step9(),
            "step10": self.step10(),
            "step11": self.step11(),
        }
