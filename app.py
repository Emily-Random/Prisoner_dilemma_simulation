# Standard library imports for random number generation, data structures, and type hints
import random  # Used for random choices
from dataclasses import dataclass  # Creates Agent class with automatic __init__ and fields
from typing import Dict, List, Tuple  # Type annotations for better code clarity

# Dash framework imports for building web interface
from dash import Dash, dcc, html, Input, Output, State  # Dash: main app, dcc: interactive components, html: HTML elements, Input/Output/State: callback dependencies
from dash.dependencies import ALL  # Used to handle multiple inputs with same ID pattern
import plotly.graph_objects as go  # Plotly for creating interactive charts (line graphs, bar charts)

# Type alias: StrategyName is just a string representing the name of a strategy
StrategyName = str

# Data class representing a single agent in the simulation
@dataclass
class Agent:
    strategy: StrategyName  # The strategy this agent follows (e.g., "Tit-for-Tat", "Always Defect")
    score: float = 0.0  # Accumulated payoff score from playing Prisoner's Dilemma rounds


# Function: Calculate payoffs for a single round of Prisoner's Dilemma
def play_round(
    action_a: str,  # Action of player A: 'C' (cooperate) or 'D' (defect)
    action_b: str,  # Action of player B: 'C' (cooperate) or 'D' (defect)
    payoff_matrix: Dict[Tuple[str, str], Tuple[float, float]],  # Dictionary mapping (action_a, action_b) -> (payoff_a, payoff_b)
) -> Tuple[float, float]:  # Returns (payoff_for_player_a, payoff_for_player_b)
    """Return payoffs for a single round given both actions."""
    return payoff_matrix[(action_a, action_b)]  # Look up the payoff tuple for this action combination


# Function: Determines the next action a strategy should take based on game history
def decide_action(
    strategy: StrategyName,  # Name of the strategy (e.g., "Tit-for-Tat", "Always Defect")
    history_self: List[str],  # List of this agent's previous actions in current encounter (e.g., ["C", "C", "D"])
    history_opp: List[str],  # List of opponent's previous actions in current encounter
) -> str:  # Returns 'C' (cooperate) or 'D' (defect)
    """Decide next action ('C' or 'D') based on strategy and history."""
    # Strategy: Always Cooperate - unconditionally cooperates every round
    if strategy == "Always Cooperate":
        return "C"  # Always return cooperate
    
    # Strategy: Always Defect - unconditionally defects every round
    if strategy == "Always Defect":
        return "D"  # Always return defect
    
    # Strategy: Random - makes random choice each round (50/50 chance)
    if strategy == "Random":
        return random.choice(["C", "D"])  # Randomly choose between cooperate and defect

    # Strategy: Tit-for-Tat - starts by cooperating, then copies opponent's last move
    if strategy == "Tit-for-Tat":
        if not history_opp:  # If no history exists (first round of encounter)
            return "C"  # Start with cooperation
        return history_opp[-1]  # Copy opponent's last action

    # Strategy: Grudge - cooperates until opponent defects once, then always defects
    if strategy == "Grudge":
        # If opponent has ever defected in this encounter, always defect
        if "D" in history_opp:  # Check if opponent has defected at least once
            return "D"  # Switch to permanent defection
        return "C"  # Continue cooperating if opponent hasn't defected yet

    # Strategy: Prober - mostly cooperates, but occasionally defects during long cooperation streaks
    if strategy == "Prober":
        # Simplified implementation:
        # Mostly cooperate, but in long cooperation streaks occasionally defect.
        if len(history_self) >= 4 and all(  # If at least 4 rounds have passed
            a == "C" and b == "C" for a, b in zip(history_self, history_opp)  # AND both players have cooperated all rounds
        ):
            # 10% chance to defect in the middle of a long cooperation train
            return "D" if random.random() < 0.10 else "C"  # 10% chance to probe with defection
        # Otherwise, 90% cooperate, 10% defect (baseline behavior)
        return "C" if random.random() < 0.90 else "D"  # 90% chance to cooperate, 10% to defect

    # Fallback: if strategy not recognized, default to cooperation
    return "C"


# Function: Simulates a multi-round Prisoner's Dilemma encounter between two agents
def play_encounter(
    agent_a: Agent,  # First agent participating in the encounter
    agent_b: Agent,  # Second agent participating in the encounter
    rounds: int,  # Number of rounds to play (iterated Prisoner's Dilemma)
    payoff_matrix: Dict[Tuple[str, str], Tuple[float, float]],  # Payoff matrix for calculating scores
) -> None:  # Returns nothing; modifies agent scores directly
    """Play an iterated PD encounter between two agents and update scores."""
    history_a: List[str] = []  # Track agent A's actions during this encounter (for strategies that use history)
    history_b: List[str] = []  # Track agent B's actions during this encounter
    for _ in range(rounds):  # Loop through each round
        # Each agent decides its action based on its strategy and history of this encounter
        action_a = decide_action(agent_a.strategy, history_a, history_b)  # Agent A chooses action
        action_b = decide_action(agent_b.strategy, history_b, history_a)  # Agent B chooses action (note: histories swapped)
        payoff_a, payoff_b = play_round(action_a, action_b, payoff_matrix)  # Calculate payoffs for this round
        agent_a.score += payoff_a  # Add this round's payoff to agent A's total score
        agent_b.score += payoff_b  # Add this round's payoff to agent B's total score
        history_a.append(action_a)  # Record agent A's action for next round's decision
        history_b.append(action_b)  # Record agent B's action for next round's decision


# Function: Creates the standard Prisoner's Dilemma payoff matrix
def build_payoff_matrix(T: float, R: float, P: float, S: float):
    """
    Build standard Prisoner's Dilemma payoff matrix.
    Actions: 'C' = cooperate, 'D' = defect.
    Returns dict mapping (action_a, action_b) -> (payoff_a, payoff_b).
    """
    # T = Temptation (defect when opponent cooperates)
    # R = Reward (both cooperate)
    # P = Punishment (both defect)
    # S = Sucker's payoff (cooperate when opponent defects)
    # Standard PD conditions: T > R > P > S and 2R > T + S
    return {
        ("C", "C"): (R, R),  # Both cooperate: both get R (reward)
        ("C", "D"): (S, T),  # A cooperates, B defects: A gets S (sucker), B gets T (temptation)
        ("D", "C"): (T, S),  # A defects, B cooperates: A gets T (temptation), B gets S (sucker)
        ("D", "D"): (P, P),  # Both defect: both get P (punishment)
    }


# Function: Creates the initial population of agents with specified strategy proportions
def initialise_population(
    population_size: int,  # Total number of agents to create
    proportions: Dict[StrategyName, float]  # Dictionary mapping strategy names to their initial proportions (may not sum to 1)
) -> List[Agent]:  # Returns list of Agent objects
    agents: List[Agent] = []  # Initialize empty list to store agents
    # Normalise proportions to sum to 1 (ensures valid probability distribution)
    total = sum(max(v, 0.0) for v in proportions.values())  # Sum all positive proportions
    if total <= 0:  # If all proportions are zero or negative (error case)
        # fallback: uniform over non-zero keys
        non_zero = [k for k, v in proportions.items() if v > 0]  # Find strategies with positive proportions
        if not non_zero:  # If no positive proportions, use all strategies
            non_zero = list(proportions.keys())
        weight = 1.0 / len(non_zero)  # Calculate equal weight for each strategy
        proportions = {k: (weight if k in non_zero else 0.0) for k in proportions}  # Set uniform proportions
        total = 1.0  # Total is now 1.0

    norm_props = {k: max(v, 0.0) / total for k, v in proportions.items()}  # Normalize: divide each by total so they sum to 1

    allocated = 0  # Counter for tracking allocated agents (not used later, but kept for debugging)
    # Create agents according to normalized proportions
    for name, prop in norm_props.items():  # Iterate through each strategy and its proportion
        count = int(round(prop * population_size))  # Calculate how many agents for this strategy (round to nearest integer)
        for _ in range(count):  # Create that many agents with this strategy
            agents.append(Agent(strategy=name))  # Add new agent with this strategy
            allocated += 1  # Increment counter
    # Adjust to exact population size (handles rounding errors)
    while len(agents) < population_size:  # If we have fewer agents than needed (due to rounding down)
        agents.append(Agent(strategy=random.choice(list(norm_props.keys()))))  # Add random strategy agent until we reach target
    while len(agents) > population_size and agents:  # If we have more agents than needed (due to rounding up)
        agents.pop()  # Remove extra agents until we reach target
    return agents  # Return the final population list


# Function: Creates the next generation by eliminating low-scoring agents and allowing survivors to reproduce
def reproduce_population(
    agents: List[Agent],  # Current generation of agents (with scores from playing games)
    eliminate_bottom_percent: float,  # Percentage (0-100) of lowest-scoring agents to eliminate
    mutation_rate: float,  # Probability (0-1) that an offspring will have a random strategy instead of parent's
    strategy_names: List[StrategyName],  # List of all possible strategy names (for mutation)
) -> List[Agent]:  # Returns new generation of agents
    """Form next generation using elimination and reproduction with mutation."""
    population_size = len(agents)  # Store original population size
    if population_size == 0:  # Edge case: empty population
        return []  # Return empty list

    # Sort by score ascending, lower scores first (worst performers at start, best at end)
    sorted_agents = sorted(agents, key=lambda a: a.score)  # Sort agents by their score (lowest first)
    bottom_fraction = max(0.0, min(1.0, eliminate_bottom_percent / 100.0))  # Convert percentage to fraction, clamp to [0, 1]
    num_eliminate = int(round(bottom_fraction * population_size))  # Calculate how many agents to eliminate
    survivors = sorted_agents[num_eliminate:] if num_eliminate < population_size else []  # Keep agents above elimination threshold

    if not survivors:  # Edge case: all agents would be eliminated
        # fallback: keep best single agent
        survivors = [sorted_agents[-1]]  # Keep the highest-scoring agent

    next_gen: List[Agent] = []  # Initialize list for new generation
    # Build new generation of fixed size, sampling survivors with replacement
    for _ in range(population_size):  # Create same number of agents as original population
        parent = random.choice(survivors)  # Randomly select a survivor to be parent
        child_strategy = parent.strategy  # Offspring inherits parent's strategy by default
        if random.random() < mutation_rate and strategy_names:  # Check if mutation occurs
            # Mutate to any strategy (including possibly the same one)
            child_strategy = random.choice(strategy_names)  # Replace with random strategy
        next_gen.append(Agent(strategy=child_strategy))  # Add new agent to next generation
    return next_gen  # Return the new generation


# Function: Records the composition (counts and proportions) of strategies in the current population
def record_composition(
    agents: List[Agent],  # Current population of agents
    strategy_names: List[StrategyName],  # List of all possible strategy names (for consistent ordering)
    generation: int,  # Current generation number (for tracking when this snapshot was taken)
) -> Dict:  # Returns dictionary with generation number, counts, and proportions
    """Record counts and proportions of each strategy."""
    counts = {name: 0 for name in strategy_names}  # Initialize count dictionary with all strategies set to 0
    for a in agents:  # Iterate through each agent
        if a.strategy in counts:  # If agent's strategy is in our tracking list
            counts[a.strategy] += 1  # Increment count for this strategy
    total = len(agents) if agents else 1  # Calculate total population size (avoid division by zero)
    proportions = {k: v / total for k, v in counts.items()}  # Calculate proportion (0-1) for each strategy
    return {
        "generation": generation,  # Generation number when this snapshot was taken
        "counts": counts,  # Dictionary of strategy name -> count (how many agents have this strategy)
        "proportions": proportions,  # Dictionary of strategy name -> proportion (0-1, fractions of population)
    }


# Function: Main simulation loop that runs the evolutionary Prisoner's Dilemma simulation
def run_simulation(
    population_size: int,  # Total number of agents in the population
    strategy_proportions: Dict[StrategyName, float],  # Initial proportions of each strategy (will be normalized)
    T: float,  # Temptation payoff (defect when opponent cooperates)
    R: float,  # Reward payoff (both cooperate)
    P: float,  # Punishment payoff (both defect)
    S: float,  # Sucker's payoff (cooperate when opponent defects)
    total_generations: int,  # Number of generations to simulate
    record_every: int,  # Record population composition every N generations (plus generation 0)
    rounds_per_encounter: int,  # Number of Prisoner's Dilemma rounds each pair plays
    eliminate_bottom_percent: float,  # Percentage of lowest-scoring agents eliminated each generation
    mutation_rate: float,  # Probability that offspring gets random strategy instead of parent's
    random_seed: int | None = None,  # Optional seed for reproducibility (None = random)
):
    if random_seed is not None:  # If seed provided, set random seed for reproducibility
        random.seed(random_seed)  # Initialize random number generator with seed

    strategy_names = list(strategy_proportions.keys())  # Get list of strategy names from input dictionary
    payoff_matrix = build_payoff_matrix(T, R, P, S)  # Create payoff matrix from T, R, P, S values

    agents = initialise_population(population_size, strategy_proportions)  # Create initial population with specified proportions
    records: List[Dict] = []  # List to store snapshots of population composition over time

    # Record generation 0 (initial state before any evolution)
    records.append(record_composition(agents, strategy_names, 0))  # Save initial population composition

    for gen in range(1, total_generations + 1):  # Loop through each generation (1 to total_generations)
        # Reset scores each generation (scores accumulate during encounters, reset between generations)
        for a in agents:  # Iterate through all agents
            a.score = 0.0  # Reset score to 0 for new generation

        # Random pairing: pair agents randomly to play against each other
        shuffled = agents[:]  # Create copy of agents list (don't modify original)
        random.shuffle(shuffled)  # Randomly shuffle the list
        # If odd population, last one simply doesn't play (pairs are formed, odd one out sits out)
        for i in range(0, len(shuffled) - 1, 2):  # Loop through pairs (step by 2: 0, 2, 4, ...)
            play_encounter(  # Have two agents play an iterated Prisoner's Dilemma
                shuffled[i],  # First agent in pair
                shuffled[i + 1],  # Second agent in pair
                rounds_per_encounter,  # Number of rounds to play
                payoff_matrix,  # Payoff matrix for calculating scores
            )

        # Reproduce next generation: eliminate worst performers and let survivors reproduce
        agents = reproduce_population(  # Create next generation based on current generation's performance
            agents,  # Current generation (with scores from encounters)
            eliminate_bottom_percent=eliminate_bottom_percent,  # Percent to eliminate
            mutation_rate=mutation_rate,  # Mutation probability
            strategy_names=strategy_names,  # Available strategies for mutation
        )

        if record_every > 0 and gen % record_every == 0:  # Check if we should record this generation
            records.append(record_composition(agents, strategy_names, gen))  # Save snapshot of current composition

    return records  # Return list of all recorded snapshots (for plotting and terminal output)


# List of all available strategies in the simulation (used for UI inputs and tracking)
AVAILABLE_STRATEGIES: List[StrategyName] = [
    "Always Cooperate",  # Strategy that always cooperates
    "Always Defect",  # Strategy that always defects
    "Prober",  # Strategy that mostly cooperates but occasionally probes with defection
    "Grudge",  # Strategy that cooperates until opponent defects, then always defects
    "Tit-for-Tat",  # Strategy that starts cooperatively and copies opponent's last move
    "Random",  # Strategy that makes random choices
]

# Create Dash application instance (main web app object)
app = Dash(__name__)  # __name__ tells Dash where to look for assets folder if needed

# Define the main layout of the web page using CSS Grid
app.layout = html.Div(
    style={
        "display": "grid",  # Use CSS Grid layout system
        "gridTemplateColumns": "20% 1fr 20%",  # Three columns: left panel 20%, center flexible, right panel 20%
        "gridTemplateRows": "auto 220px",  # Two rows: top row auto-sized, bottom row fixed 220px
        "gridTemplateAreas": '"left center right" "bottom bottom bottom"',  # Grid areas: left/center/right on top, bottom spans full width
        "height": "100vh",  # Full viewport height (100% of browser window)
        "gap": "8px",  # 8px gap between grid cells
        "padding": "8px",  # 8px padding around entire grid
        "fontFamily": "Arial, sans-serif",  # Default font family for text
        "boxSizing": "border-box",  # Include padding/border in width calculations
    },
    children=[  # List of child components (panels) in the layout
        # Left-hand panel: user inputs (all simulation parameters)
        html.Div(
            style={
                "gridArea": "left",  # Place this div in the "left" grid area
                "border": "1px solid #ccc",  # Gray border around panel
                "padding": "8px",  # 8px padding inside panel
                "overflowY": "auto",  # Allow vertical scrolling if content overflows
            },
            children=[
                html.H3("Simulation Inputs", style={"fontSize": "18px"}),  # Panel title heading
                html.Label("Population size"),  # Label for population size input
                dcc.Input(  # Dash Core Component: number input field
                    id="population-size",  # Unique ID used to reference this input in callbacks
                    type="number",  # HTML input type: number
                    min=2,  # Minimum value allowed (need at least 2 agents to pair)
                    step=1,  # Increment/decrement step size
                    value=200,  # Default value shown in input field
                    style={"width": "100%", "marginBottom": "6px"},  # Full width, 6px margin below
                ),
                html.Label("Total generations"),  # Label: how many generations to simulate
                dcc.Input(
                    id="total-generations",  # ID for callback access
                    type="number",
                    min=1,  # Must simulate at least 1 generation
                    step=1,
                    value=200,  # Default: 200 generations
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.Label("Generations per recording"),  # Label: how often to record/save population state
                dcc.Input(
                    id="record-every",  # ID for callback access
                    type="number",
                    min=1,  # Record at least every generation
                    step=1,
                    value=10,  # Default: record every 10 generations
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.Label("Rounds per encounter"),  # Label: number of PD rounds each pair plays
                dcc.Input(
                    id="rounds-per-encounter",  # ID for callback access
                    type="number",
                    min=1,  # Must play at least 1 round
                    step=1,
                    value=10,  # Default: 10 rounds per encounter
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.H4("Payoff matrix (T, R, P, S)", style={"fontSize": "16px"}),  # Section heading for payoff matrix
                html.Label("Temptation to defect (T)"),  # Label: payoff when you defect and opponent cooperates
                dcc.Input(
                    id="payoff-T",  # ID for callback access
                    type="number",
                    value=5.0,  # Default value: standard PD value
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.Label("Reward for mutual cooperation (R)"),  # Label: payoff when both cooperate
                dcc.Input(
                    id="payoff-R",  # ID for callback access
                    type="number",
                    value=3.0,  # Default value: standard PD value
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.Label("Punishment for mutual defection (P)"),  # Label: payoff when both defect
                dcc.Input(
                    id="payoff-P",  # ID for callback access
                    type="number",
                    value=1.0,  # Default value: standard PD value
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.Label("Sucker's payoff (S)"),  # Label: payoff when you cooperate and opponent defects
                dcc.Input(
                    id="payoff-S",  # ID for callback access
                    type="number",
                    value=0.0,  # Default value: standard PD value (worst outcome)
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.H4("Selection and mutation", style={"fontSize": "16px"}),  # Section heading for evolution parameters
                html.Label("Bottom percent eliminated each generation"),  # Label: selection pressure parameter
                dcc.Input(
                    id="eliminate-bottom",  # ID for callback access
                    type="number",
                    min=0,  # Minimum: 0% (no elimination)
                    max=100,  # Maximum: 100% (eliminate everyone, would cause error)
                    value=20.0,  # Default: eliminate bottom 20% each generation
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.Label("Mutation rate (0–1)"),  # Label: probability of mutation (0 = no mutation, 1 = always mutate)
                dcc.Input(
                    id="mutation-rate",  # ID for callback access
                    type="number",
                    min=0,  # Minimum: 0 (no mutations)
                    max=1,  # Maximum: 1 (always mutate)
                    step=0.01,  # Step size for decimal values
                    value=0.01,  # Default: 1% mutation rate
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.H4("Initial strategy proportions", style={"fontSize": "16px"}),  # Section heading for strategy proportions
                html.Div(
                    "Values will be normalised to sum to 1. Set 0 to exclude a strategy.",  # Helper text explaining normalization
                    style={"fontSize": "12px", "marginBottom": "4px"},  # Small font, bottom margin
                ),
                # Dynamically create input fields for each strategy using list comprehension
                *[  # Unpack list into children (allows multiple inputs)
                    html.Div(
                        children=[
                            html.Label(name, style={"fontSize": "12px"}),  # Strategy name as label
                            dcc.Input(
                                id={
                                    "type": "strategy-proportion",  # Pattern matching type for callback
                                    "index": name,  # Strategy name as index (used in callback to identify which strategy)
                                },
                                type="number",
                                min=0,  # Proportions can't be negative
                                step=0.01,  # Step size for decimal values
                                value=(
                                    0.2 if name in ["Always Cooperate", "Always Defect"] else 0.1  # Default: 20% for common strategies, 10% for others
                                ),
                                style={
                                    "width": "100%",
                                    "marginBottom": "4px",
                                },
                            ),
                        ]
                    )
                    for name in AVAILABLE_STRATEGIES  # Create one input per strategy
                ],
                html.Button(  # Button to trigger simulation run
                    "Run Simulation",  # Button text
                    id="run-simulation",  # ID for callback to detect clicks
                    n_clicks=0,  # Initial click count (increments on each click)
                    style={
                        "width": "100%",  # Full width button
                        "marginTop": "8px",  # 8px top margin
                        "padding": "8px",  # 8px padding inside button
                        "backgroundColor": "#0074D9",  # Blue background color
                        "color": "white",  # White text
                        "border": "none",  # No border
                        "cursor": "pointer",  # Pointer cursor on hover
                    },
                ),
            ],
        ),

        # Centre screen: charts (stacked line + bar) - displays simulation results
        html.Div(
            style={
                "gridArea": "center",  # Place this div in the "center" grid area
                "border": "1px solid #ccc",  # Gray border around panel
                "padding": "8px",  # 8px padding inside panel
                "display": "flex",  # Use Flexbox layout for vertical stacking
                "flexDirection": "column",  # Stack children vertically
                "gap": "8px",  # 8px gap between children
                "overflow": "hidden",  # Hide overflow content
            },
            children=[
                # Top chart: Stacked line graph showing population evolution over time
                html.Div(
                    style={"flex": "1 1 50%", "minHeight": 0},  # Takes 50% of vertical space, flexible
                    children=[
                        html.H3(
                            "Strategy populations over time",  # Chart title
                            style={"fontSize": "16px", "marginBottom": "4px"},  # Title styling
                        ),
                        dcc.Graph(  # Plotly interactive graph component
                            id="stacked-line-chart",  # ID for callback to update this chart
                            style={"height": "100%"},  # Full height of container
                            config={"displayModeBar": False},  # Hide Plotly's toolbar
                        ),
                    ],
                ),
                # Bottom chart: Bar chart showing final strategy proportions
                html.Div(
                    style={"flex": "1 1 50%", "minHeight": 0},  # Takes 50% of vertical space, flexible
                    children=[
                        html.H3(
                            "Final strategy proportions",  # Chart title
                            style={"fontSize": "16px", "marginBottom": "4px"},  # Title styling
                        ),
                        dcc.Graph(  # Plotly interactive graph component
                            id="bar-chart",  # ID for callback to update this chart
                            style={"height": "100%"},  # Full height of container
                            config={"displayModeBar": False},  # Hide Plotly's toolbar
                        ),
                    ],
                ),
            ],
        ),

        # Right-hand panel: documentation placeholder (for user to add instructions later)
        html.Div(
            style={
                "gridArea": "right",  # Place this div in the "right" grid area
                "border": "1px solid #ccc",  # Gray border around panel
                "padding": "8px",  # 8px padding inside panel
                "overflowY": "auto",  # Allow vertical scrolling if content overflows
            },
            children=[
                html.H3("Instructions", style={"fontSize": "18px"}),  # Panel title heading
                html.Div(
                    "You can edit this panel with instructions or background information.",  # Placeholder text (user will edit)
                    id="instructions-panel",  # ID for potential future callback updates
                    style={"fontSize": "13px", "whiteSpace": "pre-wrap"},  # Preserve whitespace and wrap text
                ),
            ],
        ),

        # Bottom panel: terminal / log output (displays simulation results in text format)
        html.Div(
            style={
                "gridArea": "bottom",  # Place this div in the "bottom" grid area (spans full width)
                "border": "1px solid #ccc",  # Gray border around panel
                "padding": "8px",  # 8px padding inside panel
                "overflow": "hidden",  # Hide overflow
                "display": "flex",  # Use Flexbox layout
                "flexDirection": "column",  # Stack children vertically
            },
            children=[
                html.H3("Simulation log", style={"fontSize": "16px"}),  # Panel title heading
                dcc.Textarea(  # Multi-line text area for displaying log output
                    id="terminal-output",  # ID for callback to update this textarea
                    readOnly=True,  # User cannot edit the text (read-only terminal)
                    style={
                        "width": "100%",  # Full width
                        "height": "150px",  # Fixed height of 150px
                        "fontFamily": "monospace",  # Monospace font (like terminal/console)
                        "fontSize": "11px",  # Small font size
                        "whiteSpace": "pre",  # Preserve whitespace and line breaks (don't wrap)
                        "overflow": "auto",  # Show scrollbar if content overflows
                    },
                    value="Click 'Run Simulation' to see results here.",  # Initial placeholder text
                ),
            ],
        ),
    ],
)


# Dash callback: Updates charts and terminal output when "Run Simulation" button is clicked
@app.callback(
    Output("stacked-line-chart", "figure"),  # Output 1: Update the stacked line chart figure
    Output("bar-chart", "figure"),  # Output 2: Update the bar chart figure
    Output("terminal-output", "value"),  # Output 3: Update the terminal textarea content
    Input("run-simulation", "n_clicks"),  # Input trigger: button clicks (callback runs when button clicked)
    State("population-size", "value"),  # State input: population size (value passed to function, doesn't trigger callback)
    State("total-generations", "value"),  # State input: total generations to simulate
    State("record-every", "value"),  # State input: how often to record population state
    State("rounds-per-encounter", "value"),  # State input: rounds per encounter
    State("payoff-T", "value"),  # State input: Temptation payoff
    State("payoff-R", "value"),  # State input: Reward payoff
    State("payoff-P", "value"),  # State input: Punishment payoff
    State("payoff-S", "value"),  # State input: Sucker's payoff
    State("eliminate-bottom", "value"),  # State input: bottom percent to eliminate
    State("mutation-rate", "value"),  # State input: mutation rate probability
    State({"type": "strategy-proportion", "index": ALL}, "value"),  # State input: all strategy proportions (ALL gets all inputs matching pattern)
)
# Callback function: Executes simulation and updates all outputs when triggered
def update_simulation(
    n_clicks,  # Number of times button has been clicked (from Input)
    population_size,  # Population size value (from State)
    total_generations,  # Total generations value (from State)
    record_every,  # Record every N generations value (from State)
    rounds_per_encounter,  # Rounds per encounter value (from State)
    T,  # Temptation payoff value (from State)
    R,  # Reward payoff value (from State)
    P,  # Punishment payoff value (from State)
    S,  # Sucker's payoff value (from State)
    eliminate_bottom,  # Bottom percent to eliminate value (from State)
    mutation_rate,  # Mutation rate value (from State)
    strategy_props_values,  # List of strategy proportion values (from State with ALL)
):
    # Prevent update before first click (when page first loads, n_clicks is 0)
    if not n_clicks:  # If button hasn't been clicked yet
        empty_fig = go.Figure()  # Create empty Plotly figure
        empty_fig.update_layout(  # Set basic layout for empty chart
            template="plotly_white",  # Use white background template
            xaxis_title="Generation",  # X-axis label
            yaxis_title="Population",  # Y-axis label
        )
        return empty_fig, empty_fig, "Click 'Run Simulation' to see results here."  # Return empty charts and placeholder text

    # Map strategy proportions by AVAILABLE_STRATEGIES order (convert list to dictionary)
    props: Dict[StrategyName, float] = {}  # Initialize empty dictionary for strategy proportions
    for name, val in zip(AVAILABLE_STRATEGIES, strategy_props_values or []):  # Pair each strategy name with its input value
        try:
            props[name] = float(val) if val is not None else 0.0  # Convert to float, default to 0 if None
        except (TypeError, ValueError):  # Handle invalid input (non-numeric)
            props[name] = 0.0  # Default to 0 if conversion fails

    # Ensure numeric parameters are reasonable (validate and set minimums)
    try:
        population_size = max(2, int(population_size))  # Ensure at least 2 agents (needed for pairing)
        total_generations = max(1, int(total_generations))  # Ensure at least 1 generation
        record_every = max(1, int(record_every))  # Ensure record at least every generation
        rounds_per_encounter = max(1, int(rounds_per_encounter))  # Ensure at least 1 round per encounter
        eliminate_bottom = float(eliminate_bottom or 0.0)  # Convert to float, default to 0 if None
        mutation_rate = float(mutation_rate or 0.0)  # Convert to float, default to 0 if None
    except (TypeError, ValueError):  # Handle invalid numeric inputs
        log = "Invalid numeric input. Please check your parameters."  # Error message
        return go.Figure(), go.Figure(), log  # Return empty charts and error message

    # Run the simulation with all validated parameters
    records = run_simulation(  # Execute main simulation loop, returns list of recorded snapshots
        population_size=population_size,  # Pass validated population size
        strategy_proportions=props,  # Pass strategy proportions dictionary
        T=float(T),  # Convert T to float
        R=float(R),  # Convert R to float
        P=float(P),  # Convert P to float
        S=float(S),  # Convert S to float
        total_generations=total_generations,  # Pass validated total generations
        record_every=record_every,  # Pass validated record frequency
        rounds_per_encounter=rounds_per_encounter,  # Pass validated rounds per encounter
        eliminate_bottom_percent=eliminate_bottom,  # Pass elimination percentage
        mutation_rate=mutation_rate,  # Pass mutation rate
        random_seed=42,  # Fixed seed for reproducibility (same results each run)
    )

    # Build stacked line chart: shows how population of each strategy changes over time
    generations = [rec["generation"] for rec in records]  # Extract generation numbers for x-axis
    fig_line = go.Figure()  # Create new Plotly figure
    for name in AVAILABLE_STRATEGIES:  # Iterate through each strategy
        counts = [rec["counts"][name] for rec in records]  # Extract population counts for this strategy across all recorded generations
        if all(c == 0 for c in counts):  # If strategy never appeared (all counts are 0)
            continue  # Skip this strategy (don't show on chart)
        fig_line.add_trace(  # Add a trace (line) for this strategy
            go.Scatter(  # Scatter plot (line chart)
                x=generations,  # X-axis: generation numbers
                y=counts,  # Y-axis: population counts
                mode="lines",  # Display as lines (not just points)
                name=name,  # Strategy name for legend
                stackgroup="one",  # Stack this line on top of previous ones (creates stacked area chart effect)
            )
        )
    fig_line.update_layout(  # Set chart layout properties
        template="plotly_white",  # Use white background template
        xaxis_title="Generation",  # X-axis label
        yaxis_title="Population",  # Y-axis label
        legend_title_text="Strategy",  # Legend title
    )

    # Build bar chart for final proportions: shows strategy distribution at the end of simulation
    last = records[-1]  # Get the last recorded snapshot (final generation)
    bar_x = []  # List for strategy names (x-axis labels)
    bar_y = []  # List for proportions (y-axis values)
    for name in AVAILABLE_STRATEGIES:  # Iterate through each strategy
        prop = last["proportions"][name]  # Get final proportion for this strategy
        if prop > 0:  # Only show strategies that exist in final population (proportion > 0)
            bar_x.append(name)  # Add strategy name to x-axis list
            bar_y.append(prop)  # Add proportion to y-axis list

    fig_bar = go.Figure(  # Create new Plotly figure for bar chart
        data=[
            go.Bar(  # Bar chart trace
                x=bar_x,  # X-axis: strategy names
                y=bar_y,  # Y-axis: proportions (0-1)
            )
        ]
    )
    fig_bar.update_layout(  # Set chart layout properties
        template="plotly_white",  # Use white background template
        xaxis_title="Strategy",  # X-axis label
        yaxis_title="Proportion",  # Y-axis label
        yaxis_range=[0, 1],  # Set y-axis range from 0 to 1 (proportions are 0-1)
    )

    # Build terminal log: formatted text output showing simulation results
    lines = []  # List to store lines of text for terminal output
    lines.append(  # Add simulation summary line
        f"Simulation finished: population={population_size}, generations={total_generations}"
    )
    lines.append(  # Add evolution parameters line
        f"Eliminated bottom {eliminate_bottom:.1f}% each generation, mutation rate={mutation_rate:.3f}"
    )
    lines.append("")  # Empty line for spacing
    lines.append("Recorded strategy proportions:")  # Header text
    # Create table header: "Gen" column + one column per strategy (truncated to 10 chars, padded to 12)
    header = "Gen".ljust(6) + " " + " ".join(
        name[:10].ljust(12) for name in AVAILABLE_STRATEGIES  # Truncate strategy names, pad to 12 chars
    )
    lines.append(header)  # Add header line
    for rec in records:  # Iterate through each recorded snapshot
        row = str(rec["generation"]).ljust(6)  # Start row with generation number, padded to 6 chars
        for name in AVAILABLE_STRATEGIES:  # Add proportion for each strategy
            row += " " + f"{rec['proportions'][name]:.3f}".ljust(12)  # Format as 3 decimal places, padded to 12 chars
        lines.append(row)  # Add completed row to lines list

    terminal_text = "\n".join(lines)  # Join all lines with newline characters to create final text

    return fig_line, fig_bar, terminal_text  # Return all three outputs: line chart, bar chart, terminal text


# Main execution block: runs the web server when script is executed directly
if __name__ == "__main__":  # Only run if script is executed directly (not imported as module)
    # For newer versions of Dash, use app.run instead of the deprecated app.run_server
    app.run(debug=True)  # Start Dash development server with debug mode enabled (auto-reload on code changes)


