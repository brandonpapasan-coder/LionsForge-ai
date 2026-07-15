# LionsForge AI Market Simulator Backend MVP Implementation

## Phase 7

This phase converts the simulator design into implementation requirements.

## ORM Models

Required models:

- SimulationAccount
- VirtualPosition
- TradeEvent
- MarketScenario
- PerformanceSnapshot

## Validation Schemas

Required schemas:

- AccountCreate
- TradeRequest
- PortfolioResponse
- PerformanceResponse

## Service Layer

Services:

- PortfolioService
- TradeExecutionService
- RiskService
- ScenarioService

## API Routes

Initial routes:

- POST /simulator/accounts
- GET /simulator/accounts/{id}
- POST /simulator/trades
- GET /simulator/portfolio/{id}
- POST /simulator/scenarios/run
- GET /simulator/performance/{id}

## Testing Requirements

Tests must validate:

- Account creation
- Trade execution
- Position updates
- Portfolio calculations
- Risk calculations
- Scenario replay

## Integration

The simulator connects with LionsForge AI research validation and education systems.
