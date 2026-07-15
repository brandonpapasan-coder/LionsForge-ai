# LionsForge AI Market Simulator API Contract

## Purpose
Educational paper-trading simulation layer for research validation and financial education.

## Account APIs

### Create Simulation Account
POST /simulator/accounts

Creates a virtual account with configurable starting capital.

### Get Simulation Account
GET /simulator/accounts/{account_id}

Returns balance, equity, and account status.

## Trading APIs

### Submit Simulated Trade
POST /simulator/trades

Request:
- account_id
- symbol
- side (buy/sell)
- quantity
- simulated_price

Response:
- trade event
- updated position
- updated cash balance

## Scenario APIs

### Run Market Scenario
POST /simulator/scenarios/run

Supported initial scenarios:
- bull_market
- bear_market
- volatility_event
- inflation_shock
- rate_change

## Performance APIs

GET /simulator/performance/{account_id}

Returns:
- portfolio value
- return percentage
- risk metrics
- educational feedback hooks

## Guardrails

- No live execution
- No brokerage connection
- Paper simulation only
- User-isolated data
