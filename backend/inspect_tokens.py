"""
Token Inspection Tool - Find what symbols map to specific tokens
"""
from tokens import TokenLookup

t = TokenLookup()
expiry = t.get_closest_expiry('NIFTY')
print(f"NIFTY Next Expiry: {expiry}")
print()

# Find what tokens were subscribed (from logs: 46206, 46207, 46204, 46205, 46169)
subscribed_tokens = ['46206', '46207', '46204', '46205', '46169', '46141']

print("SUBSCRIBED TOKENS (from WebSocket logs):")
for tok in subscribed_tokens:
    symbols = [k for k, v in t.symbol_map.items() if v == tok]
    if symbols:
        print(f"  Token {tok}: {symbols[0]}")
    else:
        print(f"  Token {tok}: NOT FOUND")

print()
print("BULK SUBSCRIPTION TOKENS (get_all_tokens_for_expiry):")
all_tokens = t.get_all_tokens_for_expiry('NIFTY', expiry)
print(f"  Total: {len(all_tokens)}")
print(f"  First 5: {list(all_tokens)[:5]}")

# Check if subscribed tokens are in the bulk list
print()
print("VERIFICATION:")
for tok in subscribed_tokens:
    in_bulk = tok in all_tokens
    print(f"  Token {tok} in bulk subscription: {in_bulk}")
