"""
EMERGENCY DIAGNOSTIC - Check exact frontend data state
Run this in browser console after page loads
"""

# In Browser Console(F12), paste this:

console.log('=== MARKET DATA DEBUG ===');
console.log('marketData object:', window.marketData || 'NOT EXPOSED');

# If not exposed, check React DevTools:
# 1. Open React DevTools
# 2. Find MarketProvider component
# 3. Check props / state for marketData
# 4. Check if marketData has any keys

# Also check chainData:
console.log('Option Chain Data:', window.chainData || 'NOT EXPOSED');

# Manual test - check if any data exists:
# Open Network tab, find WebSocket connection
# Check if 'market_data' messages are arriving
# Verify payload structure
