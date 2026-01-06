"""
Strategy implementations for the Prisoner's Dilemma simulation.

Each strategy is a class that implements a decision-making algorithm
based on the game history within a single encounter.
"""
from abc import ABC, abstractmethod  # Import ABC (Abstract Base Class) and abstractmethod decorator to create abstract classes
from typing import List, Optional  # Import type hints: List for lists, Optional for values that can be None
import numpy as np  # Import NumPy library for numerical operations (random number generation, arrays)


class Strategy(ABC):  # Define abstract base class that all strategies must inherit from
    """Abstract base class for all Prisoner's Dilemma strategies."""
    
    def __init__(self, name: str):  # Constructor method that initializes a strategy with a name
        """
        Initialize a strategy.
        
        Args:
            name: Human-readable name of the strategy
        """
        self.name = name  # Store the strategy's name as an instance variable
        self.reset()  # Call reset() to initialize any strategy-specific state
    
    @abstractmethod  # Decorator marking this method as abstract (must be implemented by subclasses)
    def play(self, round_num: int, opponent_history: List[int]) -> int:  # Abstract method signature: takes round number and opponent's history, returns move (0 or 1)
        """
        Determine the action for the current round.
        
        Args:
            round_num: Current round number (1-indexed)
            opponent_history: List of opponent's previous moves (0=Cooperate, 1=Defect)
        
        Returns:
            0 for Cooperate, 1 for Defect
        """
        pass  # Abstract method has no implementation - subclasses must override this
    
    def reset(self) -> None:  # Method to reset strategy state between encounters, returns nothing
        """Reset strategy state for a new encounter."""
        pass  # Default implementation does nothing - subclasses can override if needed


class AlwaysCooperate(Strategy):  # Concrete strategy class that inherits from Strategy
    """Always plays Cooperate regardless of opponent's actions."""
    
    def __init__(self):  # Constructor for AlwaysCooperate strategy
        super().__init__("Always Cooperate")  # Call parent class constructor with strategy name
    
    def play(self, round_num: int, opponent_history: List[int]) -> int:  # Implement the abstract play method
        return 0  # Always return 0 (Cooperate), ignoring round number and opponent history


class AlwaysDefect(Strategy):  # Concrete strategy class that always defects
    """Always plays Defect regardless of opponent's actions."""
    
    def __init__(self):  # Constructor for AlwaysDefect strategy
        super().__init__("Always Defect")  # Call parent class constructor with strategy name
    
    def play(self, round_num: int, opponent_history: List[int]) -> int:  # Implement the abstract play method
        return 1  # Always return 1 (Defect), ignoring round number and opponent history


class TitForTat(Strategy):  # Concrete strategy class that copies opponent's last move
    """
    Cooperates in the first round; thereafter copies the opponent's previous move.
    """
    
    def __init__(self):  # Constructor for TitForTat strategy
        super().__init__("Tit-for-Tat")  # Call parent class constructor with strategy name
    
    def play(self, round_num: int, opponent_history: List[int]) -> int:  # Implement the abstract play method
        if round_num == 1:  # Check if this is the first round of the encounter
            return 0  # Cooperate on first round (always start with cooperation)
        else:  # For all subsequent rounds
            # Copy opponent's last move
            return opponent_history[-1]  # Return the last element in opponent's history (their previous move)


class Grudge(Strategy):  # Concrete strategy class that holds a grudge after being defected on
    """
    Cooperates until the opponent defects once; thereafter always defects
    for the remainder of the encounter.
    """
    
    def __init__(self):  # Constructor for Grudge strategy
        super().__init__("Grudge")  # Call parent class constructor with strategy name
        self.opponent_defected = False  # Initialize flag to track if opponent has defected
    
    def play(self, round_num: int, opponent_history: List[int]) -> int:  # Implement the abstract play method
        # Check if opponent has defected
        if opponent_history and opponent_history[-1] == 1:  # If opponent history exists and last move was defect (1)
            self.opponent_defected = True  # Set flag to remember opponent defected
        
        if self.opponent_defected:  # If opponent has defected at any point
            return 1  # Always defect after opponent defects (hold the grudge)
        else:  # If opponent has never defected
            return 0  # Cooperate until opponent defects
    
    def reset(self) -> None:  # Override reset method to clear the grudge state
        """Reset the grudge state for a new encounter."""
        self.opponent_defected = False  # Reset flag for new encounter (forget the grudge)


class Prober(Strategy):  # Concrete strategy class that uses a probing cycle pattern
    """
    Cooperate for a random number of times between R-1 and 1, defect, then repeat the cycle.
    Note: R is the total number of rounds per encounter, set during initialization.
    """
    
    def __init__(self, total_rounds: int):  # Constructor that requires total_rounds parameter
        """
        Initialize Prober strategy.
        
        Args:
            total_rounds: Total number of rounds per encounter (R)
        """
        # Set total_rounds BEFORE calling super().__init__() because
        # the parent's __init__ calls reset() which uses self.total_rounds
        self.total_rounds = total_rounds  # Store total rounds needed for cycle generation
        self.cooperation_count = 0  # Initialize counter for how many times to cooperate in current cycle
        self.cycle_position = 0  # Initialize position tracker within current cycle
        super().__init__("Prober")  # Call parent class constructor with strategy name
        self._generate_cycle()  # Generate the initial cooperation-defect cycle
    
    def _generate_cycle(self) -> None:  # Private method to generate a new cycle pattern
        """Generate a new cooperation-defect cycle."""
        # Random number between 1 and R-1 (inclusive)
        coop_count = np.random.randint(1, self.total_rounds)  # Generate random integer from 1 to total_rounds-1
        self.cooperation_count = coop_count  # Store how many rounds to cooperate
        self.cycle_position = 0  # Reset cycle position to start of new cycle
    
    def play(self, round_num: int, opponent_history: List[int]) -> int:  # Implement the abstract play method
        # If we've completed a cycle, generate a new one
        if self.cycle_position >= self.cooperation_count + 1:  # If we've finished cooperate rounds + 1 defect round
            self._generate_cycle()  # Generate a new random cycle
        
        # Play according to cycle
        if self.cycle_position < self.cooperation_count:  # If still in cooperation phase of cycle
            action = 0  # Cooperate
        else:  # If in defect phase of cycle
            action = 1  # Defect
        
        self.cycle_position += 1  # Advance to next position in cycle
        return action  # Return the chosen action
    
    def reset(self) -> None:  # Override reset method to regenerate cycle for new encounter
        """Reset the cycle for a new encounter."""
        # Only generate cycle if total_rounds is already set (during initialization)
        if hasattr(self, 'total_rounds'):  # Check if total_rounds attribute exists (safety check)
            self._generate_cycle()  # Generate a new random cycle for the new encounter


class Random(Strategy):  # Concrete strategy class that makes random decisions
    """Cooperates or defects with equal probability each round, independently."""
    
    def __init__(self):  # Constructor for Random strategy
        super().__init__("Random")  # Call parent class constructor with strategy name
    
    def play(self, round_num: int, opponent_history: List[int]) -> int:  # Implement the abstract play method
        return np.random.randint(0, 2)  # Return random integer 0 or 1 (50% chance each) - ignores all inputs


# Strategy factory function
def create_strategy(strategy_name: str, total_rounds: int = 10) -> Strategy:  # Factory function to create strategy instances
    """
    Factory function to create strategy instances.
    
    Args:
        strategy_name: Name of the strategy to create
        total_rounds: Total rounds per encounter (needed for Prober)
    
    Returns:
        Strategy instance
    """
    strategy_map = {  # Dictionary mapping strategy names to their class constructors
        "Always Cooperate": AlwaysCooperate,  # Map "Always Cooperate" to AlwaysCooperate class
        "Always Defect": AlwaysDefect,  # Map "Always Defect" to AlwaysDefect class
        "Tit-for-Tat": TitForTat,  # Map "Tit-for-Tat" to TitForTat class
        "Grudge": Grudge,  # Map "Grudge" to Grudge class
        "Prober": lambda: Prober(total_rounds),  # Map "Prober" to lambda function that creates Prober with total_rounds
        "Random": Random,  # Map "Random" to Random class
    }
    
    if strategy_name not in strategy_map:  # Check if the requested strategy name exists in the map
        raise ValueError(f"Unknown strategy: {strategy_name}")  # Raise error if strategy doesn't exist
    
    return strategy_map[strategy_name]()  # Call the constructor from the map and return the strategy instance
