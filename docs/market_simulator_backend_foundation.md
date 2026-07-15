# LionsForge AI Market Simulator Backend Foundation

## Phase 1: Backend Foundation

The Market Simulator is an educational paper-trading sandbox. It does not execute real trades or connect to brokerages.

## Domain Models

### SimulationAccount
- id
- user_id
- starting_balance
- current_balance
- created_at

### VirtualPosition
- id
- simulation_account_id
- symbol
- quantity
- average_entry_price
- current_price

### TradeEvent
- id
- account_id
- symbol
- action
- quantity
- execution_price
- timestamp

### MarketScenario
- id
- name
- scenario_type
- parameters
- replay_seed

### PerformanceSnapshot
- id
- account_id
- portfolio_value
- return_percentage
- risk_metrics
- created_at

## API Foundation

Planned endpoints:

POST /simulator/accounts
GET /simulator/accounts/{id}
POST /simulator/trades
GET /simulator/portfolio/{id}
POST /simulator/scenarios/run
GET /simulator/performance/{id}

## Integration Targets

- Research Trust Index
- Validation Engine
- Education Hub
- Knowledge Memory

## Testing Requirements

- User isolation
- Portfolio calculation accuracy
- Scenario replay determinism
- Trade validation
- CI compatibility
