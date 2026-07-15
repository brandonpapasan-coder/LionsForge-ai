# LionsForge AI Market Simulator Database Implementation Plan

## Phase 6: Database Foundation

## Core Tables

### simulation_accounts
- id
- user_id
- starting_balance
- current_balance
- created_at

### virtual_positions
- id
- account_id
- symbol
- quantity
- entry_price
- current_price

### trade_events
- id
- account_id
- symbol
- action
- quantity
- execution_price
- timestamp

### market_scenarios
- id
- name
- scenario_type
- parameters
- replay_seed

### performance_snapshots
- id
- account_id
- portfolio_value
- return_percentage
- risk_score
- created_at

## Migration Strategy

1. Create simulator database namespace.
2. Add ORM models.
3. Add validation schemas.
4. Connect service layer.
5. Add automated database tests.

## Integration

Database layer connects:

Research Engine -> Validation Engine -> Market Simulator -> AI Mentor

## Safety

Simulation only. No live trading execution or brokerage connectivity.
