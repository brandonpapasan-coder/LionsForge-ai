# LionsForge AI Market Simulator API Backend Routes

## Phase 8 Foundation

## Account Routes

### Create Simulation Account
`POST /simulator/accounts`

Creates a paper trading environment with:
- virtual capital
- user ownership
- simulation settings

### Retrieve Account
`GET /simulator/accounts/{account_id}`

Returns:
- balance
- positions
- performance summary

---

## Trading Routes

### Execute Simulated Trade
`POST /simulator/trades`

Processes:
- buy orders
- sell orders
- position updates
- transaction history

---

## Portfolio Routes

### Portfolio Status
`GET /simulator/portfolio/{account_id}`

Returns:
- holdings
- allocation
- profit/loss
- risk indicators

---

## Scenario Routes

### Run Market Scenario
`POST /simulator/scenarios/run`

Supports:
- bull market
- bear market
- volatility event
- macro shock

---

## Intelligence Integration

Future connection points:

Research Engine -> Validation Engine -> Simulator -> AI Mentor Feedback

## Next Implementation

- FastAPI router creation
- Request schemas
- Response models
- Service bindings
