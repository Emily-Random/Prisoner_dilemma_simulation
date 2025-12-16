import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

from dash import Dash, dcc, html, Input, Output, State
from dash.dependencies import ALL
import plotly.graph_objects as go


StrategyName = str


@dataclass
class Agent:
    strategy: StrategyName
    score: float = 0.0


def play_round(
    action_a: str,
    action_b: str,
    payoff_matrix: Dict[Tuple[str, str], Tuple[float, float]],
) -> Tuple[float, float]:
    """Return payoffs for a single round given both actions."""
    return payoff_matrix[(action_a, action_b)]


def decide_action(
    strategy: StrategyName,
    history_self: List[str],
    history_opp: List[str],
) -> str:
    """Decide next action ('C' or 'D') based on strategy and history."""
    if strategy == "Always Cooperate":
        return "C"
    if strategy == "Always Defect":
        return "D"
    if strategy == "Random":
        return random.choice(["C", "D"])

    if strategy == "Tit-for-Tat":
        if not history_opp:
            return "C"
        return history_opp[-1]

    if strategy == "Grudge":
        # If opponent has ever defected in this encounter, always defect
        if "D" in history_opp:
            return "D"
        return "C"

    if strategy == "Prober":
        # Simplified implementation:
        # Mostly cooperate, but in long cooperation streaks occasionally defect.
        if len(history_self) >= 4 and all(
            a == "C" and b == "C" for a, b in zip(history_self, history_opp)
        ):
            # 10% chance to defect in the middle of a long cooperation train
            return "D" if random.random() < 0.10 else "C"
        # Otherwise, 90% cooperate, 10% defect
        return "C" if random.random() < 0.90 else "D"

    # Fallback
    return "C"


def play_encounter(
    agent_a: Agent,
    agent_b: Agent,
    rounds: int,
    payoff_matrix: Dict[Tuple[str, str], Tuple[float, float]],
) -> None:
    """Play an iterated PD encounter between two agents and update scores."""
    history_a: List[str] = []
    history_b: List[str] = []
    for _ in range(rounds):
        action_a = decide_action(agent_a.strategy, history_a, history_b)
        action_b = decide_action(agent_b.strategy, history_b, history_a)
        payoff_a, payoff_b = play_round(action_a, action_b, payoff_matrix)
        agent_a.score += payoff_a
        agent_b.score += payoff_b
        history_a.append(action_a)
        history_b.append(action_b)


def build_payoff_matrix(T: float, R: float, P: float, S: float):
    """
    Build standard Prisoner's Dilemma payoff matrix.
    Actions: 'C' = cooperate, 'D' = defect.
    Returns dict mapping (action_a, action_b) -> (payoff_a, payoff_b).
    """
    return {
        ("C", "C"): (R, R),
        ("C", "D"): (S, T),
        ("D", "C"): (T, S),
        ("D", "D"): (P, P),
    }


def initialise_population(
    population_size: int, proportions: Dict[StrategyName, float]
) -> List[Agent]:
    agents: List[Agent] = []
    # Normalise proportions to sum to 1
    total = sum(max(v, 0.0) for v in proportions.values())
    if total <= 0:
        # fallback: uniform over non-zero keys
        non_zero = [k for k, v in proportions.items() if v > 0]
        if not non_zero:
            non_zero = list(proportions.keys())
        weight = 1.0 / len(non_zero)
        proportions = {k: (weight if k in non_zero else 0.0) for k in proportions}
        total = 1.0

    norm_props = {k: max(v, 0.0) / total for k, v in proportions.items()}

    allocated = 0
    for name, prop in norm_props.items():
        count = int(round(prop * population_size))
        for _ in range(count):
            agents.append(Agent(strategy=name))
            allocated += 1
    # Adjust to exact population size
    while len(agents) < population_size:
        agents.append(Agent(strategy=random.choice(list(norm_props.keys()))))
    while len(agents) > population_size and agents:
        agents.pop()
    return agents


def reproduce_population(
    agents: List[Agent],
    eliminate_bottom_percent: float,
    mutation_rate: float,
    strategy_names: List[StrategyName],
) -> List[Agent]:
    """Form next generation using elimination and reproduction with mutation."""
    population_size = len(agents)
    if population_size == 0:
        return []

    # Sort by score ascending, lower scores first
    sorted_agents = sorted(agents, key=lambda a: a.score)
    bottom_fraction = max(0.0, min(1.0, eliminate_bottom_percent / 100.0))
    num_eliminate = int(round(bottom_fraction * population_size))
    survivors = sorted_agents[num_eliminate:] if num_eliminate < population_size else []

    if not survivors:
        # fallback: keep best single agent
        survivors = [sorted_agents[-1]]

    next_gen: List[Agent] = []
    # Build new generation of fixed size, sampling survivors with replacement
    for _ in range(population_size):
        parent = random.choice(survivors)
        child_strategy = parent.strategy
        if random.random() < mutation_rate and strategy_names:
            # Mutate to any strategy (including possibly the same one)
            child_strategy = random.choice(strategy_names)
        next_gen.append(Agent(strategy=child_strategy))
    return next_gen


def record_composition(
    agents: List[Agent],
    strategy_names: List[StrategyName],
    generation: int,
) -> Dict:
    """Record counts and proportions of each strategy."""
    counts = {name: 0 for name in strategy_names}
    for a in agents:
        if a.strategy in counts:
            counts[a.strategy] += 1
    total = len(agents) if agents else 1
    proportions = {k: v / total for k, v in counts.items()}
    return {
        "generation": generation,
        "counts": counts,
        "proportions": proportions,
    }


def run_simulation(
    population_size: int,
    strategy_proportions: Dict[StrategyName, float],
    T: float,
    R: float,
    P: float,
    S: float,
    total_generations: int,
    record_every: int,
    rounds_per_encounter: int,
    eliminate_bottom_percent: float,
    mutation_rate: float,
    random_seed: int | None = None,
):
    if random_seed is not None:
        random.seed(random_seed)

    strategy_names = list(strategy_proportions.keys())
    payoff_matrix = build_payoff_matrix(T, R, P, S)

    agents = initialise_population(population_size, strategy_proportions)
    records: List[Dict] = []

    # Record generation 0
    records.append(record_composition(agents, strategy_names, 0))

    for gen in range(1, total_generations + 1):
        # Reset scores each generation
        for a in agents:
            a.score = 0.0

        # Random pairing
        shuffled = agents[:]
        random.shuffle(shuffled)
        # If odd population, last one simply doesn't play
        for i in range(0, len(shuffled) - 1, 2):
            play_encounter(
                shuffled[i],
                shuffled[i + 1],
                rounds_per_encounter,
                payoff_matrix,
            )

        # Reproduce next generation
        agents = reproduce_population(
            agents,
            eliminate_bottom_percent=eliminate_bottom_percent,
            mutation_rate=mutation_rate,
            strategy_names=strategy_names,
        )

        if record_every > 0 and gen % record_every == 0:
            records.append(record_composition(agents, strategy_names, gen))

    return records


AVAILABLE_STRATEGIES: List[StrategyName] = [
    "Always Cooperate",
    "Always Defect",
    "Prober",
    "Grudge",
    "Tit-for-Tat",
    "Random",
]


app = Dash(__name__)

app.layout = html.Div(
    style={
        "display": "grid",
        "gridTemplateColumns": "20% 1fr 20%",
        "gridTemplateRows": "auto 220px",
        "gridTemplateAreas": '"left center right" "bottom bottom bottom"',
        "height": "100vh",
        "gap": "8px",
        "padding": "8px",
        "fontFamily": "Arial, sans-serif",
        "boxSizing": "border-box",
    },
    children=[
        # Left-hand panel: user inputs
        html.Div(
            style={
                "gridArea": "left",
                "border": "1px solid #ccc",
                "padding": "8px",
                "overflowY": "auto",
            },
            children=[
                html.H3("Simulation Inputs", style={"fontSize": "18px"}),
                html.Label("Population size"),
                dcc.Input(
                    id="population-size",
                    type="number",
                    min=2,
                    step=1,
                    value=200,
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.Label("Total generations"),
                dcc.Input(
                    id="total-generations",
                    type="number",
                    min=1,
                    step=1,
                    value=200,
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.Label("Generations per recording"),
                dcc.Input(
                    id="record-every",
                    type="number",
                    min=1,
                    step=1,
                    value=10,
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.Label("Rounds per encounter"),
                dcc.Input(
                    id="rounds-per-encounter",
                    type="number",
                    min=1,
                    step=1,
                    value=10,
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.H4("Payoff matrix (T, R, P, S)", style={"fontSize": "16px"}),
                html.Label("Temptation to defect (T)"),
                dcc.Input(
                    id="payoff-T",
                    type="number",
                    value=5.0,
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.Label("Reward for mutual cooperation (R)"),
                dcc.Input(
                    id="payoff-R",
                    type="number",
                    value=3.0,
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.Label("Punishment for mutual defection (P)"),
                dcc.Input(
                    id="payoff-P",
                    type="number",
                    value=1.0,
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.Label("Sucker's payoff (S)"),
                dcc.Input(
                    id="payoff-S",
                    type="number",
                    value=0.0,
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.H4("Selection and mutation", style={"fontSize": "16px"}),
                html.Label("Bottom percent eliminated each generation"),
                dcc.Input(
                    id="eliminate-bottom",
                    type="number",
                    min=0,
                    max=100,
                    value=20.0,
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.Label("Mutation rate (0–1)"),
                dcc.Input(
                    id="mutation-rate",
                    type="number",
                    min=0,
                    max=1,
                    step=0.01,
                    value=0.01,
                    style={"width": "100%", "marginBottom": "6px"},
                ),
                html.H4("Initial strategy proportions", style={"fontSize": "16px"}),
                html.Div(
                    "Values will be normalised to sum to 1. Set 0 to exclude a strategy.",
                    style={"fontSize": "12px", "marginBottom": "4px"},
                ),
                *[
                    html.Div(
                        children=[
                            html.Label(name, style={"fontSize": "12px"}),
                            dcc.Input(
                                id={
                                    "type": "strategy-proportion",
                                    "index": name,
                                },
                                type="number",
                                min=0,
                                step=0.01,
                                value=(
                                    0.2 if name in ["Always Cooperate", "Always Defect"] else 0.1
                                ),
                                style={
                                    "width": "100%",
                                    "marginBottom": "4px",
                                },
                            ),
                        ]
                    )
                    for name in AVAILABLE_STRATEGIES
                ],
                html.Button(
                    "Run Simulation",
                    id="run-simulation",
                    n_clicks=0,
                    style={
                        "width": "100%",
                        "marginTop": "8px",
                        "padding": "8px",
                        "backgroundColor": "#0074D9",
                        "color": "white",
                        "border": "none",
                        "cursor": "pointer",
                    },
                ),
            ],
        ),

        # Centre screen: charts (stacked line + bar)
        html.Div(
            style={
                "gridArea": "center",
                "border": "1px solid #ccc",
                "padding": "8px",
                "display": "flex",
                "flexDirection": "column",
                "gap": "8px",
                "overflow": "hidden",
            },
            children=[
                html.Div(
                    style={"flex": "1 1 50%", "minHeight": 0},
                    children=[
                        html.H3(
                            "Strategy populations over time",
                            style={"fontSize": "16px", "marginBottom": "4px"},
                        ),
                        dcc.Graph(
                            id="stacked-line-chart",
                            style={"height": "100%"},
                            config={"displayModeBar": False},
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": "1 1 50%", "minHeight": 0},
                    children=[
                        html.H3(
                            "Final strategy proportions",
                            style={"fontSize": "16px", "marginBottom": "4px"},
                        ),
                            dcc.Graph(
                            id="bar-chart",
                            style={"height": "100%"},
                            config={"displayModeBar": False},
                        ),
                    ],
                ),
            ],
        ),

        # Right-hand panel: documentation placeholder
        html.Div(
            style={
                "gridArea": "right",
                "border": "1px solid #ccc",
                "padding": "8px",
                "overflowY": "auto",
            },
            children=[
                html.H3("Instructions", style={"fontSize": "18px"}),
                html.Div(
                    "You can edit this panel with instructions or background information.",
                    id="instructions-panel",
                    style={"fontSize": "13px", "whiteSpace": "pre-wrap"},
                ),
            ],
        ),

        # Bottom panel: terminal / log output
        html.Div(
            style={
                "gridArea": "bottom",
                "border": "1px solid #ccc",
                "padding": "8px",
                "overflow": "hidden",
                "display": "flex",
                "flexDirection": "column",
            },
            children=[
                html.H3("Simulation log", style={"fontSize": "16px"}),
                dcc.Textarea(
                    id="terminal-output",
                    readOnly=True,
                    style={
                        "width": "100%",
                        "height": "150px",
                        "fontFamily": "monospace",
                        "fontSize": "11px",
                        "whiteSpace": "pre",
                        "overflow": "auto",
                    },
                    value="Click 'Run Simulation' to see results here.",
                ),
            ],
        ),
    ],
)


@app.callback(
    Output("stacked-line-chart", "figure"),
    Output("bar-chart", "figure"),
    Output("terminal-output", "value"),
    Input("run-simulation", "n_clicks"),
    State("population-size", "value"),
    State("total-generations", "value"),
    State("record-every", "value"),
    State("rounds-per-encounter", "value"),
    State("payoff-T", "value"),
    State("payoff-R", "value"),
    State("payoff-P", "value"),
    State("payoff-S", "value"),
    State("eliminate-bottom", "value"),
    State("mutation-rate", "value"),
    State({"type": "strategy-proportion", "index": ALL}, "value"),
)
def update_simulation(
    n_clicks,
    population_size,
    total_generations,
    record_every,
    rounds_per_encounter,
    T,
    R,
    P,
    S,
    eliminate_bottom,
    mutation_rate,
    strategy_props_values,
):
    # Prevent update before first click
    if not n_clicks:
        empty_fig = go.Figure()
        empty_fig.update_layout(
            template="plotly_white",
            xaxis_title="Generation",
            yaxis_title="Population",
        )
        return empty_fig, empty_fig, "Click 'Run Simulation' to see results here."

    # Map strategy proportions by AVAILABLE_STRATEGIES order
    props: Dict[StrategyName, float] = {}
    for name, val in zip(AVAILABLE_STRATEGIES, strategy_props_values or []):
        try:
            props[name] = float(val) if val is not None else 0.0
        except (TypeError, ValueError):
            props[name] = 0.0

    # Ensure numeric parameters are reasonable
    try:
        population_size = max(2, int(population_size))
        total_generations = max(1, int(total_generations))
        record_every = max(1, int(record_every))
        rounds_per_encounter = max(1, int(rounds_per_encounter))
        eliminate_bottom = float(eliminate_bottom or 0.0)
        mutation_rate = float(mutation_rate or 0.0)
    except (TypeError, ValueError):
        log = "Invalid numeric input. Please check your parameters."
        return go.Figure(), go.Figure(), log

    records = run_simulation(
        population_size=population_size,
        strategy_proportions=props,
        T=float(T),
        R=float(R),
        P=float(P),
        S=float(S),
        total_generations=total_generations,
        record_every=record_every,
        rounds_per_encounter=rounds_per_encounter,
        eliminate_bottom_percent=eliminate_bottom,
        mutation_rate=mutation_rate,
        random_seed=42,
    )

    # Build stacked line chart
    generations = [rec["generation"] for rec in records]
    fig_line = go.Figure()
    for name in AVAILABLE_STRATEGIES:
        counts = [rec["counts"][name] for rec in records]
        if all(c == 0 for c in counts):
            continue
        fig_line.add_trace(
            go.Scatter(
                x=generations,
                y=counts,
                mode="lines",
                name=name,
                stackgroup="one",
            )
        )
    fig_line.update_layout(
        template="plotly_white",
        xaxis_title="Generation",
        yaxis_title="Population",
        legend_title_text="Strategy",
    )

    # Build bar chart for final proportions
    last = records[-1]
    bar_x = []
    bar_y = []
    for name in AVAILABLE_STRATEGIES:
        prop = last["proportions"][name]
        if prop > 0:
            bar_x.append(name)
            bar_y.append(prop)

    fig_bar = go.Figure(
        data=[
            go.Bar(
                x=bar_x,
                y=bar_y,
            )
        ]
    )
    fig_bar.update_layout(
        template="plotly_white",
        xaxis_title="Strategy",
        yaxis_title="Proportion",
        yaxis_range=[0, 1],
    )

    # Build terminal log
    lines = []
    lines.append(
        f"Simulation finished: population={population_size}, generations={total_generations}"
    )
    lines.append(
        f"Eliminated bottom {eliminate_bottom:.1f}% each generation, mutation rate={mutation_rate:.3f}"
    )
    lines.append("")
    lines.append("Recorded strategy proportions:")
    header = "Gen".ljust(6) + " " + " ".join(
        name[:10].ljust(12) for name in AVAILABLE_STRATEGIES
    )
    lines.append(header)
    for rec in records:
        row = str(rec["generation"]).ljust(6)
        for name in AVAILABLE_STRATEGIES:
            row += " " + f"{rec['proportions'][name]:.3f}".ljust(12)
        lines.append(row)

    terminal_text = "\n".join(lines)

    return fig_line, fig_bar, terminal_text


if __name__ == "__main__":
    # For newer versions of Dash, use app.run instead of the deprecated app.run_server
    app.run(debug=True)


