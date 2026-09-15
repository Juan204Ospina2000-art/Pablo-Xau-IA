from engine import SetupInput, evaluate_setup

setup = SetupInput(
    direction="BUY",
    entry=3650,
    stop_loss=3640,
    take_profit=3680,
    trend_aligned=True,
    liquidity_sweep=True,
    structure_confirmation=True,
    valid_entry_zone=True,
    high_impact_news_near=False,
    price_extended=False,
)

result = evaluate_setup(setup)
print(result)
assert result.rr == 3.0
assert result.score >= 6
assert result.decision == "BUY"
print("OK")
