"""
Evolutionary simulation engine for the Prisoner's Dilemma.

This module implements the core simulation logic including pairing, interaction,
scoring, selection, and reproduction with mutation.
"""
from typing import List, Dict, Tuple, Optional  # Import type hints: List for lists, Dict for dictionaries, Tuple for tuples, Optional for nullable values
import numpy as np  # Import NumPy library for numerical operations (random shuffling, array operations)
from strategies import Strategy, create_strategy  # Import Strategy base class and factory function from strategies module


class Player:  # Class representing a single player in the simulation
    """Represents a single player in the simulation."""
    
    def __init__(self, strategy: Strategy, player_id: int):  # Constructor: initialize player with strategy and ID
        """
        Initialize a player.
        
        Args:
            strategy: The strategy this player uses
            player_id: Unique identifier for this player
        """
        self.strategy = strategy  # Store the strategy object this player uses
        self.player_id = player_id  # Store unique identifier for this player
        self.score = 0.0  # Initialize score to 0.0 (accumulated payoffs)
        self.history: List[int] = []  # Initialize empty list to store this player's move history in current encounter
    
    def reset_encounter(self) -> None:  # Method to reset player state for a new encounter, returns nothing
        """Reset player state for a new encounter."""
        self.history = []  # Clear move history (start fresh for new opponent)
        self.strategy.reset()  # Reset strategy's internal state (e.g., Grudge forgetting previous grudge)
    
    def play(self, round_num: int, opponent_history: List[int]) -> int:  # Method to make a move, returns 0 (cooperate) or 1 (defect)
        """
        Make a move in the current round.
        
        Args:
            round_num: Current round number (1-indexed)
            opponent_history: Opponent's previous moves
        
        Returns:
            0 for Cooperate, 1 for Defect
        """
        action = self.strategy.play(round_num, opponent_history)  # Get action from strategy based on round and opponent history
        self.history.append(action)  # Record this action in player's own history
        return action  # Return the chosen action (0 or 1)


class Simulation:  # Main class that runs the evolutionary simulation
    """
    Main simulation engine for evolutionary Prisoner's Dilemma.
    
    Implements the full evolutionary cycle: pairing, interaction, scoring,
    selection, and reproduction with mutation.
    """
    
    def __init__(  # Constructor: initialize simulation with all parameters
        self,
        initial_population: int,  # Parameter: starting number of players
        strategy_proportions: Dict[str, float],  # Parameter: dictionary mapping strategy names to their initial proportions
        payoff_matrix: np.ndarray,  # Parameter: 2x2 NumPy array with payoff values
        total_generations: int,  # Parameter: how many generations to simulate
        recording_interval: int,  # Parameter: record data every N generations
        rounds_per_encounter: int,  # Parameter: number of rounds each pair plays
        selection_percentile: float,  # Parameter: bottom Y% eliminated (0-1)
        mutation_rate: float,  # Parameter: probability of mutation per offspring (0-1)
        offspring_per_survivor: int = 1,  # Parameter: number of children each survivor produces (default 1)
        prober_total_rounds: Optional[int] = None,  # Parameter: total rounds for Prober strategy (optional)
    ):
        """
        Initialize the simulation.
        
        Args:
            initial_population: Initial population size N_0
            strategy_proportions: Dictionary mapping strategy names to initial proportions (must sum to 1)
            payoff_matrix: 2x2 payoff matrix [[CC, CD], [DC, DD]]
            total_generations: Total number of generations G
            recording_interval: Record data every T generations
            rounds_per_encounter: Number of rounds per encounter R
            selection_percentile: Bottom Y% eliminated each generation (0-1)
            mutation_rate: Probability Z of mutation per offspring (0-1)
            offspring_per_survivor: Number of children each surviving player produces (default: 1)
            prober_total_rounds: Total rounds for Prober strategy (optional, defaults to rounds_per_encounter)
        """
        self.initial_population = initial_population  # Store initial population size
        self.strategy_proportions = strategy_proportions  # Store strategy proportions dictionary
        self.payoff_matrix = payoff_matrix  # Store payoff matrix NumPy array
        self.total_generations = total_generations  # Store total generations to run
        self.recording_interval = recording_interval  # Store recording interval
        self.rounds_per_encounter = rounds_per_encounter  # Store rounds per encounter
        self.selection_percentile = selection_percentile  # Store selection percentile (bottom Y% eliminated)
        self.mutation_rate = mutation_rate  # Store mutation rate (probability per offspring)
        self.offspring_per_survivor = offspring_per_survivor  # Store number of offspring per survivor
        self.population_cap = 300  # Set maximum population size to 300
        # Ensure prober_total_rounds is valid (at least 2 for Prober to work)
        if prober_total_rounds is not None:  # Check if prober_total_rounds was explicitly provided
            if prober_total_rounds < 2:  # Validate it's at least 2
                raise ValueError("Prober total rounds must be at least 2")  # Raise error if invalid
            self.prober_total_rounds = prober_total_rounds  # Store the provided value
        else:  # If not provided
            # Default to rounds_per_encounter, but ensure it's at least 2
            self.prober_total_rounds = max(rounds_per_encounter, 2)  # Use rounds_per_encounter or 2, whichever is larger
        
        # Validate payoff matrix
        if payoff_matrix.shape != (2, 2):  # Check if payoff matrix is exactly 2x2
            raise ValueError("Payoff matrix must be 2x2")  # Raise error if wrong size
        
        # Validate strategy proportions sum to 1
        total_prop = sum(strategy_proportions.values())  # Sum all proportion values
        if not np.isclose(total_prop, 1.0):  # Check if sum is approximately 1.0 (using NumPy for floating-point comparison)
            raise ValueError(f"Strategy proportions must sum to 1.0, got {total_prop}")  # Raise error if sum is wrong
        
        # Initialize population
        self.players: List[Player] = []  # Initialize empty list to store Player objects
        self._initialize_population()  # Call method to create initial population
        
        # Data recording
        self.recorded_data: List[Dict] = []  # Initialize empty list to store recorded data dictionaries
        self.available_strategies = list(strategy_proportions.keys())  # Store list of strategy names that are available
    
    def _initialize_population(self) -> None:  # Private method to create initial population, returns nothing
        """Initialize the population with specified strategy proportions."""
        self.players = []  # Clear players list (should be empty, but ensure it)
        player_id = 0  # Initialize player ID counter starting at 0
        
        # Calculate number of players per strategy
        strategy_counts: Dict[str, int] = {}  # Initialize dictionary to count players per strategy
        remaining = self.initial_population  # Track remaining players to distribute (for rounding adjustments)
        
        for strategy_name, proportion in self.strategy_proportions.items():  # Iterate through each strategy and its proportion
            count = int(self.initial_population * proportion)  # Calculate number of players for this strategy (integer part)
            strategy_counts[strategy_name] = count  # Store count in dictionary
            remaining -= count  # Subtract from remaining count
        
        # Distribute remaining players to first strategy (rounding adjustment)
        if remaining > 0:  # If there are leftover players due to rounding
            first_strategy = list(self.strategy_proportions.keys())[0]  # Get first strategy name
            strategy_counts[first_strategy] += remaining  # Add remaining players to first strategy
        
        # Create players
        for strategy_name, count in strategy_counts.items():  # Iterate through each strategy and its count
            for _ in range(count):  # Create 'count' number of players with this strategy
                # Use prober_total_rounds for Prober, otherwise rounds_per_encounter
                rounds_for_strategy = self.prober_total_rounds if strategy_name == "Prober" else self.rounds_per_encounter  # Choose appropriate rounds value
                strategy = create_strategy(strategy_name, rounds_for_strategy)  # Create strategy instance using factory function
                player = Player(strategy, player_id)  # Create Player object with strategy and ID
                self.players.append(player)  # Add player to players list
                player_id += 1  # Increment player ID for next player
        
        # Shuffle to randomize order
        np.random.shuffle(self.players)  # Randomly shuffle players list using NumPy
    
    def _pair_players(self) -> List[Tuple[Player, Player]]:  # Private method to pair players, returns list of player pairs
        """
        Randomly pair players into disjoint pairs.
        
        Returns:
            List of (player1, player2) tuples
        """
        players_copy = self.players.copy()  # Create copy of players list (to avoid modifying original)
        np.random.shuffle(players_copy)  # Randomly shuffle the copy using NumPy
        
        pairs = []  # Initialize empty list to store pairs
        for i in range(0, len(players_copy) - 1, 2):  # Iterate through indices, stepping by 2 (0, 2, 4, ...)
            pairs.append((players_copy[i], players_copy[i + 1]))  # Pair adjacent players and add to pairs list
        
        # If odd number of players, last one doesn't play this generation
        return pairs  # Return list of player pairs
    
    def _play_encounter(self, player1: Player, player2: Player) -> None:  # Private method to play encounter between two players, returns nothing
        """
        Execute R rounds of Prisoner's Dilemma between two players.
        
        Args:
            player1: First player
            player2: Second player
        """
        # Reset encounter state
        player1.reset_encounter()  # Reset player1's state for new encounter
        player2.reset_encounter()  # Reset player2's state for new encounter
        
        # Play R rounds
        for round_num in range(1, self.rounds_per_encounter + 1):  # Iterate from round 1 to rounds_per_encounter
            # Get moves
            move1 = player1.play(round_num, player2.history)  # Player1 makes move based on round and player2's history
            move2 = player2.play(round_num, player1.history)  # Player2 makes move based on round and player1's history
            
            # Calculate payoffs
            payoff1 = self.payoff_matrix[move1, move2]  # Get player1's payoff: matrix[row=move1, col=move2]
            payoff2 = self.payoff_matrix[move2, move1]  # Get player2's payoff: matrix[row=move2, col=move1]
            
            # Update scores
            player1.score += payoff1  # Add payoff1 to player1's total score
            player2.score += payoff2  # Add payoff2 to player2's total score
    
    def _select_survivors(self) -> List[Player]:  # Private method to select survivors, returns list of surviving players
        """
        Select survivors based on bottom Y% elimination.
        
        Returns:
            List of surviving players
        """
        if not self.players:  # Check if players list is empty
            return []  # Return empty list if no players
        
        # Sort players by score (descending)
        sorted_players = sorted(self.players, key=lambda p: p.score, reverse=True)  # Sort players by score, highest first
        
        # Calculate number to eliminate
        num_to_eliminate = int(len(sorted_players) * self.selection_percentile)  # Calculate how many players to eliminate (bottom Y%)
        
        # Return survivors (top players)
        return sorted_players[num_to_eliminate:]  # Return slice from index num_to_eliminate to end (top players)
    
    def _reproduce(self, survivors: List[Player]) -> List[Player]:  # Private method to create offspring, returns list of new players
        """
        Create offspring from survivors with mutation.
        
        Args:
            survivors: List of surviving players
        
        Returns:
            List of new generation players
        """
        new_players = []  # Initialize empty list to store new generation players
        player_id = max([p.player_id for p in self.players], default=-1) + 1  # Get highest existing player ID and add 1 for next ID
        
        for parent in survivors:  # Iterate through each surviving player (parent)
            # Each survivor produces offspring_per_survivor children
            for _ in range(self.offspring_per_survivor):  # Loop to create multiple offspring per parent
                # Apply mutation
                if np.random.random() < self.mutation_rate:  # Check if mutation occurs (random number < mutation rate)
                    # Mutate to a different random strategy
                    available_strategies = [  # Create list of strategies that are different from parent's strategy
                        s for s in self.available_strategies  # Iterate through all available strategies
                        if s != parent.strategy.name  # Include only strategies different from parent's
                    ]
                    if available_strategies:  # Check if there are alternative strategies available
                        new_strategy_name = np.random.choice(available_strategies)  # Randomly choose one alternative strategy
                        # Use prober_total_rounds for Prober, otherwise rounds_per_encounter
                        rounds_for_strategy = self.prober_total_rounds if new_strategy_name == "Prober" else self.rounds_per_encounter  # Choose appropriate rounds value
                        offspring_strategy = create_strategy(  # Create new strategy instance
                            new_strategy_name, rounds_for_strategy  # Pass strategy name and rounds value
                        )
                    else:  # If no alternative strategies available (shouldn't happen normally)
                        # No alternative strategies available, use parent's strategy
                        parent_strategy_name = parent.strategy.name  # Get parent's strategy name
                        rounds_for_strategy = self.prober_total_rounds if parent_strategy_name == "Prober" else self.rounds_per_encounter  # Choose appropriate rounds value
                        offspring_strategy = create_strategy(  # Create strategy instance (same as parent)
                            parent_strategy_name, rounds_for_strategy  # Pass parent's strategy name and rounds value
                        )
                else:  # If no mutation occurs
                    # No mutation: create a new instance of the parent's strategy
                    # This ensures each player has their own strategy object
                    parent_strategy_name = parent.strategy.name  # Get parent's strategy name
                    # Use prober_total_rounds for Prober, otherwise rounds_per_encounter
                    rounds_for_strategy = self.prober_total_rounds if parent_strategy_name == "Prober" else self.rounds_per_encounter  # Choose appropriate rounds value
                    offspring_strategy = create_strategy(  # Create new strategy instance (same type as parent)
                        parent_strategy_name, rounds_for_strategy  # Pass parent's strategy name and rounds value
                    )
                
                # Create new player
                offspring = Player(offspring_strategy, player_id)  # Create new Player object with strategy and ID
                offspring.score = parent.score  # Inherit parent's score for population capping (used later for ranking)
                new_players.append(offspring)  # Add offspring to new players list
                player_id += 1  # Increment player ID for next offspring
        
        return new_players  # Return list of all new generation players
    
    def _get_strategy_counts(self) -> Dict[str, int]:  # Private method to count strategies, returns dictionary mapping strategy names to counts
        """
        Count players by strategy in current population.
        
        Returns:
            Dictionary mapping strategy names to counts
        """
        counts: Dict[str, int] = {}  # Initialize empty dictionary to store counts
        for player in self.players:  # Iterate through each player in population
            strategy_name = player.strategy.name  # Get player's strategy name
            counts[strategy_name] = counts.get(strategy_name, 0) + 1  # Increment count for this strategy (default 0 if not seen before)
        return counts  # Return dictionary with strategy counts
    
    def _record_data(self, generation: int) -> None:  # Private method to record population data, returns nothing
        """
        Record population data at current generation.
        
        Args:
            generation: Current generation number
        """
        strategy_counts = self._get_strategy_counts()  # Get dictionary of strategy name to count
        total_pop = len(self.players)  # Get total population size
        
        # Calculate proportions
        proportions = {  # Create dictionary comprehension to calculate proportions
            name: count / total_pop if total_pop > 0 else 0.0  # Calculate proportion (count/total), or 0.0 if no population
            for name, count in strategy_counts.items()  # Iterate through each strategy and its count
        }
        
        # Ensure all strategies are represented (with 0 if absent)
        for strategy_name in self.available_strategies:  # Iterate through all available strategies
            if strategy_name not in proportions:  # Check if strategy is missing from proportions
                proportions[strategy_name] = 0.0  # Add strategy with 0.0 proportion
        
        record = {  # Create dictionary to store recorded data
            "generation": generation,  # Include generation number
            "population_size": total_pop,  # Include total population size
            "strategy_counts": strategy_counts,  # Include strategy counts dictionary
            "strategy_proportions": proportions,  # Include strategy proportions dictionary
        }
        
        self.recorded_data.append(record)  # Add record to recorded_data list
    
    def run(self) -> List[Dict]:  # Public method to run the complete simulation, returns list of recorded data dictionaries
        """
        Run the complete simulation.
        
        Returns:
            List of recorded data dictionaries
        """
        self.recorded_data = []  # Clear any previous recorded data
        
        # Record initial state
        self._record_data(0)  # Record data for generation 0 (initial state)
        
        # Run generations
        for generation in range(1, self.total_generations + 1):  # Iterate from generation 1 to total_generations
            # Reset scores for new generation
            for player in self.players:  # Iterate through each player
                player.score = 0.0  # Reset player's score to 0.0 for new generation
            
            # Pairing
            pairs = self._pair_players()  # Randomly pair players into pairs
            
            # Interaction
            for player1, player2 in pairs:  # Iterate through each pair
                self._play_encounter(player1, player2)  # Play encounter between the two players
            
            # Selection
            survivors = self._select_survivors()  # Select survivors (eliminate bottom Y%)
            
            # Check if we have survivors
            if len(survivors) == 0:  # Check if no players survived
                # No survivors, simulation ends
                break  # Exit generation loop early
            
            # Reproduction
            new_players = self._reproduce(survivors)  # Create offspring from survivors (with mutation)
            
            # Apply population cap: if population exceeds cap, keep top players by score
            if len(new_players) > self.population_cap:  # Check if population exceeds cap (300)
                # Offspring already have parent scores assigned in _reproduce
                # Sort all new players by their inherited parent scores (descending)
                sorted_players = sorted(new_players, key=lambda p: p.score, reverse=True)  # Sort by score, highest first
                # Keep only the top 300 players
                self.players = sorted_players[:self.population_cap]  # Take only first 300 players (slice to population_cap)
            else:  # If population is within cap
                self.players = new_players  # Use all new players as next generation
            
            # Record data at intervals
            if generation % self.recording_interval == 0:  # Check if this generation should be recorded (divisible by interval)
                self._record_data(generation)  # Record data for this generation
        
        # Record final state if not already recorded
        if self.total_generations % self.recording_interval != 0:  # Check if final generation wasn't already recorded
            self._record_data(self.total_generations)  # Record data for final generation
        
        return self.recorded_data  # Return list of all recorded data dictionaries
