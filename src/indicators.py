import math, datetime, logging

log = logging.getLogger("VWAPCalc")

class VWAPCalculator:
    """Daily anchored VWAP + up to 3 bands."""
    def __init__(self, mode="stdev", mults=(1,2,3)):
        self.mode, self.mults = mode, mults
        self.reset()

    def reset(self):
        self.spv = self.sv = self.sp2v = 0.0
        self.day = None

    def update(self, bar):
        ts,o,h,l,c,v = bar
        d = datetime.date.fromtimestamp(ts)
        if self.day and d != self.day:
            self.reset()
        self.day = d

        tp = (h+l+c)/3
        self.spv  += tp*v
        self.sp2v += tp*tp*v
        self.sv   += v
        vwap = self.spv/self.sv if self.sv else float("nan")
        var  = self.sp2v/self.sv - vwap*vwap
        sd   = math.sqrt(var) if var>0 else 0

        log.debug(f"{self.day}  VWAP={vwap:.2f}  SD={sd:.4f}")

        basis = sd if self.mode=="stdev" else vwap*0.01
        bands = [(vwap+basis*m, vwap-basis*m) for m in self.mults]
        return {"vwap": vwap, "bands": bands}
