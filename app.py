"""
Flask backend API for the Prisoner's Dilemma simulation.

Provides endpoints for running simulations and retrieving results.
"""
from flask import Flask, request, jsonify, render_template  # Import Flask web framework components: Flask app, request handling, JSON responses, HTML templates
from flask_cors import CORS  # Import CORS (Cross-Origin Resource Sharing) to allow frontend-backend communication
import numpy as np  # Import NumPy for array operations (converting payoff matrix)
from simulation import Simulation  # Import the Simulation class from simulation module

app = Flask(__name__)  # Create Flask application instance with current module name
CORS(app)  # Enable CORS for frontend communication (allows JavaScript to make API calls)

# Store active simulation state
active_simulation: Simulation = None  # Global variable to store currently running simulation (or None if none active)
simulation_results = []  # Global variable to store results from completed simulations


@app.route('/')  # Decorator: register this function to handle requests to root URL '/'
def index():  # Function to serve the main HTML page
    """Serve the main application page."""
    return render_template('index.html')  # Return the HTML template file to the browser


@app.route('/project-details')  # Decorator: register this function to handle requests to '/project-details'
def project_details():  # Function to serve the detailed project documentation page
    """Serve the detailed project documentation page."""
    return render_template('project_details.html')  # Return the detailed documentation HTML template file to the browser


@app.route('/api/run_simulation', methods=['POST'])  # Decorator: register endpoint for POST requests to '/api/run_simulation'
def run_simulation():  # Function to handle simulation run requests
    """
    Run a complete simulation with given parameters.
    
    Expected JSON payload:
    {
        "initial_population": int,
        "strategy_proportions": {strategy_name: float, ...},
        "payoff_matrix": [[CC, CD], [DC, DD]],
        "total_generations": int,
        "recording_interval": int,
        "rounds_per_encounter": int,
        "selection_percentile": float,
        "mutation_rate": float
    }
    """
    global active_simulation, simulation_results  # Declare we're modifying global variables
    
    try:  # Start try block to catch and handle errors
        data = request.json  # Extract JSON data from HTTP request body
        
        # Extract parameters
        initial_population = int(data['initial_population'])  # Convert initial population to integer
        strategy_proportions = data['strategy_proportions']  # Get dictionary of strategy names to proportions
        payoff_matrix = np.array(data['payoff_matrix'], dtype=float)  # Convert payoff matrix list to NumPy array of floats
        total_generations = int(data['total_generations'])  # Convert total generations to integer
        recording_interval = int(data['recording_interval'])  # Convert recording interval to integer
        rounds_per_encounter = int(data['rounds_per_encounter'])  # Convert rounds per encounter to integer
        selection_percentile = float(data['selection_percentile'])  # Convert selection percentile to float
        mutation_rate = float(data['mutation_rate'])  # Convert mutation rate to float
        offspring_per_survivor = int(data.get('offspring_per_survivor', 1))  # Get offspring per survivor (default 1 if not provided)
        prober_total_rounds = data.get('prober_total_rounds', None)  # Get Prober total rounds (optional, defaults to None)
        if prober_total_rounds is not None:  # Check if prober_total_rounds was provided
            prober_total_rounds = int(prober_total_rounds)  # Convert to integer
            if prober_total_rounds < 2:  # Validate that it's at least 2
                return jsonify({"error": "Prober total rounds must be at least 2"}), 400  # Return error response with HTTP 400 status
        
        # Validate parameters
        if initial_population < 2:  # Check if initial population is too small
            return jsonify({"error": "Initial population must be at least 2"}), 400  # Return error with HTTP 400 status
        
        if rounds_per_encounter < 1:  # Check if rounds per encounter is invalid
            return jsonify({"error": "Rounds per encounter must be at least 1"}), 400  # Return error with HTTP 400 status
        
        if selection_percentile < 0 or selection_percentile >= 1:  # Check if selection percentile is out of valid range [0, 1)
            return jsonify({"error": "Selection percentile must be in [0, 1)"}), 400  # Return error with HTTP 400 status
        
        if mutation_rate < 0 or mutation_rate > 1:  # Check if mutation rate is out of valid range [0, 1]
            return jsonify({"error": "Mutation rate must be in [0, 1]"}), 400  # Return error with HTTP 400 status
        
        if offspring_per_survivor < 1:  # Check if offspring per survivor is invalid
            return jsonify({"error": "Offspring per survivor must be at least 1"}), 400  # Return error with HTTP 400 status
        
        # Create and run simulation
        simulation = Simulation(  # Create new Simulation instance with all parameters
            initial_population=initial_population,  # Pass initial population size
            strategy_proportions=strategy_proportions,  # Pass strategy proportions dictionary
            payoff_matrix=payoff_matrix,  # Pass payoff matrix NumPy array
            total_generations=total_generations,  # Pass total number of generations
            recording_interval=recording_interval,  # Pass recording interval
            rounds_per_encounter=rounds_per_encounter,  # Pass rounds per encounter
            selection_percentile=selection_percentile,  # Pass selection percentile
            mutation_rate=mutation_rate,  # Pass mutation rate
            offspring_per_survivor=offspring_per_survivor,  # Pass offspring per survivor
            prober_total_rounds=prober_total_rounds,  # Pass Prober total rounds (may be None)
        )
        
        results = simulation.run()  # Execute the simulation and get results
        active_simulation = simulation  # Store simulation in global variable for potential later access
        simulation_results = results  # Store results in global variable
        
        return jsonify({  # Return successful response as JSON
            "success": True,  # Indicate success
            "results": results,  # Include simulation results
            "message": f"Simulation completed: {len(results)} data points recorded"  # Include success message with count
        })
    
    except ValueError as e:  # Catch ValueError exceptions (invalid parameter values)
        return jsonify({"error": f"Invalid parameter: {str(e)}"}), 400  # Return error message with HTTP 400 status
    except Exception as e:  # Catch any other unexpected exceptions
        import traceback  # Import traceback module for detailed error information
        error_details = traceback.format_exc()  # Get full error traceback as string
        print(f"Simulation error: {error_details}")  # Log error details to console for debugging
        return jsonify({"error": f"Simulation failed: {str(e)}"}), 500  # Return error message with HTTP 500 status


@app.route('/api/get_results', methods=['GET'])  # Decorator: register endpoint for GET requests to '/api/get_results'
def get_results():  # Function to retrieve simulation results
    """Get the results from the last simulation."""
    global simulation_results  # Declare we're accessing global variable
    
    if not simulation_results:  # Check if no results are available
        return jsonify({"error": "No simulation results available"}), 404  # Return error with HTTP 404 status
    
    return jsonify({  # Return results as JSON
        "success": True,  # Indicate success
        "results": simulation_results  # Include the stored results
    })


@app.route('/api/get_current_state', methods=['GET'])  # Decorator: register endpoint for GET requests to '/api/get_current_state'
def get_current_state():  # Function to get current simulation state (for animation)
    """
    Get the current state of the active simulation (for animation mode).
    Returns None if no simulation is active.
    """
    global active_simulation  # Declare we're accessing global variable
    
    if active_simulation is None:  # Check if no simulation is currently active
        return jsonify({"success": False, "state": None})  # Return failure response with no state
    
    # Get current strategy counts
    strategy_counts = active_simulation._get_strategy_counts()  # Get dictionary of strategy name to count
    total_pop = len(active_simulation.players)  # Get total number of players in current population
    
    # Get player positions and strategies for visualization
    players_data = []  # Initialize empty list to store player data
    for player in active_simulation.players:  # Iterate through each player in simulation
        players_data.append({  # Add dictionary with player information to list
            "id": player.player_id,  # Include player's unique ID
            "strategy": player.strategy.name,  # Include player's strategy name
            "score": player.score  # Include player's current score
        })
    
    return jsonify({  # Return state as JSON
        "success": True,  # Indicate success
        "state": {  # Include state dictionary
            "population_size": total_pop,  # Include total population size
            "strategy_counts": strategy_counts,  # Include strategy counts dictionary
            "players": players_data  # Include list of player data dictionaries
        }
    })


@app.route('/api/health', methods=['GET'])  # Decorator: register endpoint for GET requests to '/api/health'
def health():  # Function for health check endpoint
    """Health check endpoint."""
    return jsonify({"status": "healthy"})  # Return simple JSON indicating server is healthy


if __name__ == '__main__':  # Check if script is being run directly (not imported)
    app.run(debug=True, port=5000)  # Start Flask development server on port 5000 with debug mode enabled
