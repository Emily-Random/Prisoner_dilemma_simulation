# Prisoner's Dilemma Evolution Simulation

A web-based simulation of how different strategies for the Prisoner's Dilemma evolve over time under explicit evolutionary rules, based on population size, strategy set, payoff matrix, and selection dynamics.

## Features

- **Six Strategy Types**: Always Cooperate, Always Defect, Tit-for-Tat, Grudge, Prober, and Random
- **Evolutionary Dynamics**: Population-based evolution with selection, reproduction, and mutation
- **Interactive Web Interface**: 
  - Left panel: Parameter controls
  - Center panel: Dual visualization modes (Statistical View and Agent Animation)
  - Right panel: Documentation area
  - Bottom panel: Terminal output with exact proportions
- **High-Performance Backend**: NumPy-optimized simulation engine with vectorized operations
- **Dark Theme UI**: Modern dark interface with high-contrast colors

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

3. Configure simulation parameters:
   - Set initial population size
   - Select strategies and set initial proportions
   - Configure payoff matrix
   - Set evolution parameters (generations, selection, mutation rate)

4. Click "Run Simulation" to execute

5. View results in:
   - **Statistical View**: Population size over time (line chart) and current strategy proportions (bar chart)
   - **Agent Animation**: Visual representation of players arranged in a circle, with pairing animations

## Project Structure

```
Prisoner_dilemma_simulation/
├── app.py                 # Flask backend API
├── simulation.py          # Core simulation engine
├── strategies.py          # Strategy implementations
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Main web interface
└── static/
    ├── style.css         # Dark theme styling
    └── app.js            # Frontend JavaScript
```

## Strategy Descriptions

- **Always Cooperate**: Always plays Cooperate
- **Always Defect**: Always plays Defect
- **Tit-for-Tat**: Cooperates first, then copies opponent's last move
- **Grudge**: Cooperates until opponent defects, then always defects
- **Prober**: Cooperates for random rounds (1 to R-1), defects, then repeats
- **Random**: 50% chance of cooperate or defect each round

## License

MIT License - see LICENSE file for details
