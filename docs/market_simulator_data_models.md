# LionsForge AI Market Simulator

## Backend Data Model Foundation

## SimulationAccount
Represents an educational paper trading account.

Fields:
- id
- user_id
- account_name
- starting_balance
- current_balance
- created_at

## VirtualPosition
Tracks simulated holdings.

Fields:
- id
- account_id
- symbol
- quantity
- average_entry_price
- current_price
- unrealized_pnl

## TradeEvent
Stores simulated transactions.

Fields:
- id
- account_id
- symbol
- action
- quantity
- execution_price
- timestamp

## MarketScenario
Defines controlled simulation environments.

Fields:
- id
- name
- scenario_type
- parameters
- replay_seed

## PerformanceSnapshot
Captures learning and evaluation metrics.

Fields:
- id
- account_id
- portfolio_value
- return_percentage
- volatility_score
- risk_score
- timestamp

## Service Layer Requirements

- Portfolio calculation engine
- Risk calculation service
- Scenario replay engine
- AI mentor feedback service
- Research validation connector
