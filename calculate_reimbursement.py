from math import exp

# Iteration-1 champion constants
BASE_PD = 99.9158
BONUS_DAY5 = 44.08837
RATE_0_100 = 0.446456
RATE_101_500 = 0.3182
RATE_501_800 = 0.24
RATE_801P = 0.18
REC_CAP_LOW = 300.0
REC_CAP_HIGH = 1150.77
ROUND_OFFSET = -3.23459
CURVE_A = -0.0002
PEAK_SPEND = 700.0
CURVE_B = 150.0
EFF_CTR = 200.0
EFF_WDTH = 150.0
EFF_AMPL = 25.0
RCPT_BUMP = 2.50
SECOND_WEEK_PENALTY = 12.0
CENTS_BUG_F = 0.457
MILE_CAP_RATE = 0.25
REC_CAP_RATE = 0.15
MULT_1D = 1.15
MULT_5D = 0.92
MULT_7D = 1.25
MULT_9D = 0.85
MULT_14D = 1.20


def _cents(amount: float) -> float:
    """Round to nearest cent using the legacy offset."""
    return round(amount + ROUND_OFFSET, 2)


def _trip_multiplier(d: float, r: float, m: float) -> float:
    if d <= 2:
        return MULT_1D
    if d == 5:
        return MULT_5D
    if 7 <= d <= 8 and r > 900:
        return MULT_7D
    if 9 <= d <= 13 and r > 1200:
        return MULT_9D
    if d >= 14 and m / max(d, 1) > 180:
        return MULT_14D
    return 1.0


def reimburse(days: float, miles: float, receipts: float) -> float:
    """Compute reimbursement using the champion rule set."""
    total = 0.0

    # Base per diem and day-5 bonus
    total += _cents(BASE_PD * days)
    if days == 5:
        total += _cents(BONUS_DAY5)

    # Mileage tiers
    total += _cents(RATE_0_100 * min(miles, 100))
    total += _cents(RATE_101_500 * max(min(miles, 500) - 100, 0))
    total += _cents(RATE_501_800 * max(min(miles, 800) - 500, 0))
    total += _cents(RATE_801P * max(miles - 800, 0))

    # Receipt curve with quadratic adjustment around the peak spend
    spend_adj = CURVE_A * (receipts - PEAK_SPEND) ** 2 + receipts
    spend_adj = max(0.0, min(spend_adj, REC_CAP_HIGH))
    total += _cents(spend_adj)

    # Efficiency bonus centered on miles per day
    if days > 0:
        eff = EFF_AMPL * exp(-((miles / days - EFF_CTR) / EFF_WDTH) ** 2)
        total += _cents(eff)

    # Receipt bump once receipts exceed the lower cap
    if receipts > REC_CAP_LOW:
        total += _cents(RCPT_BUMP)

    # Penalty for trips beyond a week
    if days > 7:
        total -= _cents(SECOND_WEEK_PENALTY * (days - 7))

    # Excess mileage and receipt caps
    total += _cents(MILE_CAP_RATE * max(miles - 800, 0))
    total += _cents(REC_CAP_RATE * max(receipts - 1800, 0))

    # Rounding bug factor
    if receipts % 1 in {0.49, 0.99}:
        total *= CENTS_BUG_F

    # Length-based multiplier
    total *= _trip_multiplier(days, receipts, miles)

    return _cents(total)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 4:
        print("Usage: python calculate_reimbursement.py <days> <miles> <receipts>")
        raise SystemExit(1)
    d, m, r = map(float, sys.argv[1:])
    print(reimburse(d, m, r))
