/**
 * Main application JavaScript for Prisoner's Dilemma Evolution Simulation
 * Handles UI interactions, API communication, and visualizations
 */

// Global state
let currentResults = [];
let currentMode = 'statistical';
let populationChart = null;
let proportionChart = null;
let animationCanvas = null;
let animationCtx = null;
let animationInterval = null;
let animationState = 'night'; // 'night' or 'day'
let animationPlayers = [];
let animationPairs = [];
let strategyColors = {};
let animationPlaying = false;
let animationGenerationIndex = 0;
let previousGenerationPlayers = [];
let eliminatedPlayers = [];
let newbornPlayers = [];
let encounterResults = []; // Store encounter results: [{pair: [p1, p2], winner: p1/p2, startTime: timestamp}]
let currentEncounterIndex = 0;
let dayPhase = 'moving'; // 'moving', 'interacting', 'showing_result', 'returning'
let dayStartTime = 0;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeUI();
    setupEventListeners();
    initializeCharts();
    updateStrategyProportions();
    updateProberInputVisibility();
});

/**
 * Initialize UI components
 */
function initializeUI() {
    // Set default strategy colors
    const strategies = ['Always Cooperate', 'Always Defect', 'Tit-for-Tat', 'Grudge', 'Prober', 'Random'];
    const colors = ['#00ff00', '#ff0000', '#00ffff', '#ffff00', '#ff00ff', '#ff8800'];
    strategies.forEach((strategy, idx) => {
        strategyColors[strategy] = colors[idx] || '#ffffff';
    });
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Strategy checkboxes
    document.querySelectorAll('.strategy-check').forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            updateStrategyProportions();
            updateProberInputVisibility();
        });
    });
    
    // Prober rounds input sync with rounds_per_encounter
    const proberInput = document.getElementById('prober_total_rounds');
    const roundsInput = document.getElementById('rounds_per_encounter');
    if (proberInput && roundsInput) {
        roundsInput.addEventListener('input', (e) => {
            if (proberInput.value === String(parseInt(proberInput.value))) {
                proberInput.value = e.target.value;
            }
        });
    }
    
    // Run button
    document.getElementById('run-button').addEventListener('click', runSimulation);
    
    // Validate proportions on input
    document.querySelectorAll('#strategy-proportions input').forEach(input => {
        input.addEventListener('input', validateProportions);
    });
}

/**
 * Update Prober input visibility based on checkbox
 */
function updateProberInputVisibility() {
    const proberChecked = document.querySelector('.strategy-check[value="Prober"]').checked;
    const proberGroup = document.getElementById('prober-rounds-group');
    if (proberGroup) {
        proberGroup.style.display = proberChecked ? 'block' : 'none';
    }
}

/**
 * Update strategy proportion inputs based on selected strategies
 */
function updateStrategyProportions() {
    const container = document.getElementById('strategy-proportions');
    container.innerHTML = '';
    
    const selectedStrategies = Array.from(document.querySelectorAll('.strategy-check:checked'))
        .map(cb => cb.value);
    
    if (selectedStrategies.length === 0) {
        container.innerHTML = '<p style="color: #ff6666;">Please select at least one strategy</p>';
        return;
    }
    
    // Default values: 0.2 for first 5 strategies, 0 for Random
    const defaultValues = {
        'Always Cooperate': '0.2',
        'Always Defect': '0.2',
        'Tit-for-Tat': '0.2',
        'Grudge': '0.2',
        'Prober': '0.2',
        'Random': '0.0'
    };
    
    selectedStrategies.forEach(strategy => {
        const item = document.createElement('div');
        item.className = 'strategy-proportion-item';
        
        const label = document.createElement('label');
        label.textContent = strategy + ':';
        
        const input = document.createElement('input');
        input.type = 'number';
        const defaultValue = defaultValues[strategy] !== undefined ? defaultValues[strategy] : '0.0';
        input.value = defaultValue;
        input.min = '0';
        input.max = '1';
        input.step = '0.001';
        input.dataset.strategy = strategy;
        
        // Ensure the value is displayed
        input.setAttribute('value', defaultValue);
        
        item.appendChild(label);
        item.appendChild(input);
        container.appendChild(item);
    });
    
    validateProportions();
}

/**
 * Validate that proportions sum to 1.0
 */
function validateProportions() {
    const inputs = document.querySelectorAll('#strategy-proportions input');
    const sum = Array.from(inputs).reduce((acc, input) => {
        return acc + parseFloat(input.value || 0);
    }, 0);
    
    const statusMessage = document.getElementById('status-message');
    if (Math.abs(sum - 1.0) > 0.001) {
        statusMessage.textContent = `Warning: Proportions sum to ${sum.toFixed(3)} (should be 1.0)`;
        statusMessage.className = 'status-message error';
    } else {
        statusMessage.textContent = '';
        statusMessage.className = 'status-message';
    }
}

// Mode switching removed - only statistical view is available

/**
 * Initialize Chart.js charts
 */
function initializeCharts() {
    // Population chart (stacked area/line)
    const popCtx = document.getElementById('population-chart').getContext('2d');
    populationChart = new Chart(popCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: []
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Population Size Over Time',
                    color: '#00ff00'
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#ffffff'
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Generation',
                        color: '#00ff00'
                    },
                    ticks: { color: '#ffffff' },
                    grid: { color: '#333366' }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Population Size',
                        color: '#00ff00'
                    },
                    ticks: { color: '#ffffff' },
                    grid: { color: '#333366' }
                }
            }
        }
    });
    
    // Proportion chart (bar chart)
    const propCtx = document.getElementById('proportion-chart').getContext('2d');
    proportionChart = new Chart(propCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Proportion',
                data: [],
                backgroundColor: []
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Strategy Proportions (Current Generation)',
                    color: '#00ff00'
                },
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Strategy',
                        color: '#00ff00'
                    },
                    ticks: { color: '#ffffff' },
                    grid: { color: '#333366' }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Proportion',
                        color: '#00ff00'
                    },
                    ticks: { color: '#ffffff' },
                    grid: { color: '#333366' },
                    min: 0,
                    max: 1
                }
            }
        }
    });
}

/**
 * Initialize animation canvas
 */
function initializeAnimation() {
    animationCanvas = document.getElementById('animation-canvas');
    animationCtx = animationCanvas.getContext('2d');
    
    // Set canvas size
    resizeAnimationCanvas();
    window.addEventListener('resize', resizeAnimationCanvas);
}

/**
 * Resize animation canvas to fit container
 */
function resizeAnimationCanvas() {
    if (!animationCanvas) return;
    
    const container = animationCanvas.parentElement;
    if (!container) return;
    
    // Get actual container dimensions
    const rect = container.getBoundingClientRect();
    const width = rect.width || container.clientWidth || 800;
    const height = rect.height || container.clientHeight || 600;
    
    // Only resize if dimensions are valid
    if (width > 0 && height > 0) {
        animationCanvas.width = width;
        animationCanvas.height = height;
        
        // Redraw if we have players and are in animation mode
        if (animationPlayers.length > 0 && currentMode === 'animation') {
            drawNightView();
        }
    }
}

/**
 * Run simulation
 */
async function runSimulation() {
    const button = document.getElementById('run-button');
    button.disabled = true;
    button.textContent = 'Running...';
    
    const statusMessage = document.getElementById('status-message');
    statusMessage.textContent = 'Starting simulation...';
    statusMessage.className = 'status-message';
    
    try {
        // Collect parameters
        const params = collectParameters();
        
        // Validate
        if (!validateParameters(params)) {
            return;
        }
        
        // Call API
        const response = await fetch('/api/run_simulation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(params)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Simulation failed');
        }
        
        // Store results
        currentResults = data.results;
        
        // Update visualizations
        updateStatisticalView();
        updateTerminalOutput();
        
        statusMessage.textContent = data.message;
        statusMessage.className = 'status-message success';
        
    } catch (error) {
        statusMessage.textContent = `Error: ${error.message}`;
        statusMessage.className = 'status-message error';
        console.error('Simulation error:', error);
    } finally {
        button.disabled = false;
        button.textContent = 'Run Simulation';
    }
}

/**
 * Collect parameters from UI
 */
function collectParameters() {
    const selectedStrategies = Array.from(document.querySelectorAll('.strategy-check:checked'))
        .map(cb => cb.value);
    
    const strategyProportions = {};
    selectedStrategies.forEach(strategy => {
        const input = document.querySelector(`#strategy-proportions input[data-strategy="${strategy}"]`);
        strategyProportions[strategy] = parseFloat(input.value);
    });
    
    const params = {
        initial_population: parseInt(document.getElementById('initial_population').value),
        strategy_proportions: strategyProportions,
        payoff_matrix: [
            [parseFloat(document.getElementById('payoff_CC').value), parseFloat(document.getElementById('payoff_CD').value)],
            [parseFloat(document.getElementById('payoff_DC').value), parseFloat(document.getElementById('payoff_DD').value)]
        ],
        total_generations: parseInt(document.getElementById('total_generations').value),
        recording_interval: parseInt(document.getElementById('recording_interval').value),
        rounds_per_encounter: parseInt(document.getElementById('rounds_per_encounter').value),
        selection_percentile: parseFloat(document.getElementById('selection_percentile').value),
        mutation_rate: parseFloat(document.getElementById('mutation_rate').value),
        offspring_per_survivor: parseInt(document.getElementById('offspring_per_survivor').value)
    };
    
    // Add prober_total_rounds if Prober is selected
    if (selectedStrategies.includes('Prober')) {
        const proberInput = document.getElementById('prober_total_rounds');
        if (proberInput) {
            params.prober_total_rounds = parseInt(proberInput.value);
        }
    }
    
    return params;
}

/**
 * Validate parameters
 */
function validateParameters(params) {
    const statusMessage = document.getElementById('status-message');
    
    // Check proportions sum
    const propSum = Object.values(params.strategy_proportions).reduce((a, b) => a + b, 0);
    if (Math.abs(propSum - 1.0) > 0.001) {
        statusMessage.textContent = `Error: Strategy proportions must sum to 1.0 (got ${propSum.toFixed(3)})`;
        statusMessage.className = 'status-message error';
        return false;
    }
    
    if (params.initial_population < 2) {
        statusMessage.textContent = 'Error: Initial population must be at least 2';
        statusMessage.className = 'status-message error';
        return false;
    }
    
    return true;
}

/**
 * Update statistical view with results
 */
function updateStatisticalView() {
    if (!currentResults || currentResults.length === 0) return;
    
    // Extract data
    const generations = currentResults.map(r => r.generation);
    const strategies = Object.keys(currentResults[0].strategy_proportions);
    
    // Prepare datasets for population chart
    const datasets = strategies.map(strategy => {
        return {
            label: strategy,
            data: currentResults.map(r => {
                const count = r.strategy_counts[strategy] || 0;
                return count;
            }),
            borderColor: strategyColors[strategy] || '#ffffff',
            backgroundColor: (strategyColors[strategy] || '#ffffff') + '40',
            fill: true,
            tension: 0.4
        };
    });
    
    // Update population chart
    populationChart.data.labels = generations;
    populationChart.data.datasets = datasets;
    populationChart.update();
    
    // Update proportion chart with latest generation
    const latest = currentResults[currentResults.length - 1];
    proportionChart.data.labels = strategies;
    proportionChart.data.datasets[0].data = strategies.map(s => latest.strategy_proportions[s] || 0);
    proportionChart.data.datasets[0].backgroundColor = strategies.map(s => strategyColors[s] || '#ffffff');
    proportionChart.update();
}

/**
 * Update terminal output
 */
function updateTerminalOutput() {
    const terminal = document.getElementById('terminal-output');
    terminal.innerHTML = '';
    
    if (!currentResults || currentResults.length === 0) {
        terminal.innerHTML = '<div class="terminal-line">No simulation data available.</div>';
        return;
    }
    
    currentResults.forEach(record => {
        const genLine = document.createElement('div');
        genLine.className = 'terminal-line generation';
        genLine.textContent = `Generation ${record.generation}: Population = ${record.population_size}`;
        terminal.appendChild(genLine);
        
        Object.entries(record.strategy_proportions).forEach(([strategy, proportion]) => {
            const stratLine = document.createElement('div');
            stratLine.className = 'terminal-line strategy';
            stratLine.textContent = `${strategy}: ${(proportion * 100).toFixed(2)}%`;
            terminal.appendChild(stratLine);
        });
    });
    
    // Scroll to bottom
    terminal.scrollTop = terminal.scrollHeight;
}

/**
 * Start animation mode
 */
function startAnimation() {
    // Stop any existing animation
    pauseAnimationPlayback();
    
    // Ensure canvas is properly sized
    resizeAnimationCanvas();
    
    if (currentResults && currentResults.length > 0) {
        setupAnimationFromResults();
    } else {
        // Show empty state
        animationPlayers = [];
        previousGenerationPlayers = [];
        eliminatedPlayers = [];
        newbornPlayers = [];
        animationState = 'night';
        drawNightView();
    }
}

/**
 * Setup animation from simulation results
 */
function setupAnimationFromResults() {
    if (!currentResults || currentResults.length === 0) {
        animationPlayers = [];
        previousGenerationPlayers = [];
        eliminatedPlayers = [];
        newbornPlayers = [];
        animationState = 'night';
        drawNightView();
        return;
    }
    
    // Start from first generation
    animationGenerationIndex = 0;
    const currentState = currentResults[animationGenerationIndex];
    setupAnimationPlayers(currentState);
    previousGenerationPlayers = [];
    eliminatedPlayers = [];
    newbornPlayers = [];
    animationState = 'night';
    
    // Ensure canvas is ready
    resizeAnimationCanvas();
    
    // Draw initial state
    drawNightView();
    updateGenerationInfo();
}

/**
 * Start animation playback (real-time recording)
 */
function startAnimationPlayback() {
    if (!currentResults || currentResults.length === 0) {
        return;
    }
    
    animationPlaying = true;
    document.getElementById('animation-play-button').style.display = 'none';
    document.getElementById('animation-pause-button').style.display = 'inline-block';
    
    // Reset to first generation
    animationGenerationIndex = 0;
    setupAnimationFromResults();
    
    // Play through generations
    playNextGeneration();
}

/**
 * Play next generation in sequence
 */
function playNextGeneration() {
    if (!animationPlaying || animationGenerationIndex >= currentResults.length) {
        pauseAnimationPlayback();
        return;
    }
    
    const state = currentResults[animationGenerationIndex];
    const previousState = animationGenerationIndex > 0 ? currentResults[animationGenerationIndex - 1] : null;
    
    // Calculate eliminated and newborn players
    if (previousState) {
        calculatePlayerChanges(previousState, state);
    } else {
        eliminatedPlayers = [];
        newbornPlayers = [];
        // All initial players are newborns
        newbornPlayers = [...animationPlayers];
    }
    
    // Setup players for this generation
    setupAnimationPlayers(state);
    
    // Show night view with eliminations and births
    animationState = 'night';
    dayPhase = 'night';
    currentEncounterIndex = 0;
    encounterResults = [];
    animationPairs = []; // Clear pairs for night
    drawNightView();
    updateGenerationInfo();
    
    // After 2 seconds, show day view
    setTimeout(() => {
        if (!animationPlaying) return;
        animationState = 'day';
        dayPhase = 'moving';
        dayStartTime = Date.now();
        startDayPhase();
    }, 2000);
}

/**
 * Start day phase with encounters
 */
function startDayPhase() {
    if (!animationPlaying || animationState !== 'day') return;
    
    const activePlayers = animationPlayers.filter(p => !eliminatedPlayers.includes(p));
    if (activePlayers.length < 2) {
        // Not enough players, return to night
        returnToNight();
        return;
    }
    
    // Create pairs - ensure all players are paired
    animationPairs = [];
    const shuffledPlayers = [...activePlayers].sort(() => Math.random() - 0.5);
    
    for (let i = 0; i < shuffledPlayers.length - 1; i += 2) {
        animationPairs.push([shuffledPlayers[i], shuffledPlayers[i + 1]]);
    }
    
    // Initialize pair positions for random movement within circle
    initializePairPositions();
    
    // Start first encounter
    currentEncounterIndex = 0;
    startEncounter();
}

/**
 * Initialize pair positions for random movement
 */
function initializePairPositions() {
    const width = animationCanvas.width;
    const height = animationCanvas.height;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.35;
    
    // Assign random positions within circle for each pair, keeping pairs together
    animationPairs.forEach((pair, pairIndex) => {
        // Random angle and distance from center
        const angle = Math.random() * 2 * Math.PI;
        const distance = Math.random() * radius * 0.6; // Keep within inner 60% of circle
        
        const pairCenterX = centerX + distance * Math.cos(angle);
        const pairCenterY = centerY + distance * Math.sin(angle);
        
        // Place players close together (adjacent)
        const offset = 15; // Distance between paired players
        const perpAngle = angle + Math.PI / 2;
        
        pair[0].x = pairCenterX + offset * Math.cos(perpAngle);
        pair[0].y = pairCenterY + offset * Math.sin(perpAngle);
        pair[0].targetX = pair[0].x;
        pair[0].targetY = pair[0].y;
        pair[0].vx = (Math.random() - 0.5) * 2; // Random velocity
        pair[0].vy = (Math.random() - 0.5) * 2;
        pair[0].score = 0;
        
        pair[1].x = pairCenterX - offset * Math.cos(perpAngle);
        pair[1].y = pairCenterY - offset * Math.sin(perpAngle);
        pair[1].targetX = pair[1].x;
        pair[1].targetY = pair[1].y;
        pair[1].vx = (Math.random() - 0.5) * 2;
        pair[1].vy = (Math.random() - 0.5) * 2;
        pair[1].score = 0;
    });
}

/**
 * Start an encounter
 */
function startEncounter() {
    if (currentEncounterIndex >= animationPairs.length) {
        // All encounters complete, return to night
        returnToNight();
        return;
    }
    
    const pair = animationPairs[currentEncounterIndex];
    dayPhase = 'interacting';
    
    // Simulate encounter result (winner based on random or strategy)
    // For simplicity, randomly determine winner, but in real sim this would use actual scores
    const winner = Math.random() > 0.5 ? pair[0] : pair[1];
    const loser = winner === pair[0] ? pair[1] : pair[0];
    
    encounterResults.push({
        pair: pair,
        winner: winner,
        loser: loser,
        startTime: Date.now()
    });
    
    // After 0.5 seconds, show result
    setTimeout(() => {
        if (!animationPlaying || animationState !== 'day') return;
        dayPhase = 'showing_result';
        // Draw result view
        drawDayView();
        
        // Show result for 0.3 seconds, then move to next encounter
        setTimeout(() => {
            if (!animationPlaying || animationState !== 'day') return;
            dayPhase = 'interacting'; // Reset phase for next encounter
            currentEncounterIndex++;
            startEncounter(); // Move to next encounter
        }, 300);
    }, 500);
}

/**
 * Return to night phase
 */
function returnToNight() {
    if (!animationPlaying) return;
    
    dayPhase = 'returning';
    
    // Move all players back to circle border
    const activePlayers = animationPlayers.filter(p => !eliminatedPlayers.includes(p));
    const width = animationCanvas.width;
    const height = animationCanvas.height;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.35;
    const angleStep = (2 * Math.PI) / activePlayers.length;
    
    activePlayers.forEach((player, index) => {
        const angle = index * angleStep;
        player.targetX = centerX + radius * Math.cos(angle);
        player.targetY = centerY + radius * Math.sin(angle);
    });
    
    // Animate return to border
    let returnFrameCount = 0;
    const returnAnimation = () => {
        if (!animationPlaying || returnFrameCount > 30) {
            // Return complete, show eliminated players in red, then remove
            showEliminatedPlayers();
            return;
        }
        
        activePlayers.forEach(player => {
            player.x += (player.targetX - player.x) * 0.2;
            player.y += (player.targetY - player.y) * 0.2;
        });
        
        drawDayView();
        returnFrameCount++;
        requestAnimationFrame(returnAnimation);
    };
    
    returnAnimation();
}

/**
 * Show eliminated players in red, then remove them
 */
function showEliminatedPlayers() {
    if (!animationPlaying) return;
    
    if (eliminatedPlayers.length === 0) {
        // No eliminations, move to next generation
        eliminatedPlayers = [];
        newbornPlayers = [];
        animationGenerationIndex++;
        if (animationPlaying && animationGenerationIndex < currentResults.length) {
            playNextGeneration();
        } else {
            pauseAnimationPlayback();
        }
        return;
    }
    
    // Show eliminated players in red for 1 second
    animationState = 'night';
    dayPhase = 'showing_eliminated';
    
    // Draw with eliminated players visible
    let frameCount = 0;
    const showEliminatedAnimation = () => {
        if (!animationPlaying || frameCount > 60) { // Show for ~1 second
            // Remove eliminated players
            animationPlayers = animationPlayers.filter(p => !eliminatedPlayers.includes(p));
            eliminatedPlayers = [];
            newbornPlayers = [];
            dayPhase = 'night';
            
            // Move to next generation
            animationGenerationIndex++;
            if (animationPlaying && animationGenerationIndex < currentResults.length) {
                playNextGeneration();
            } else {
                pauseAnimationPlayback();
            }
            return;
        }
        
        // Draw night view showing eliminated players in red
        drawNightViewWithEliminated([...eliminatedPlayers]);
        frameCount++;
        if (animationPlaying) {
            requestAnimationFrame(showEliminatedAnimation);
        }
    };
    
    showEliminatedAnimation();
}

/**
 * Draw night view with eliminated players shown in red
 */
function drawNightViewWithEliminated(eliminatedToShow) {
    if (!animationCtx || !animationCanvas) return;
    
    const width = animationCanvas.width;
    const height = animationCanvas.height;
    
    if (width === 0 || height === 0) {
        resizeAnimationCanvas();
        const newWidth = animationCanvas.width;
        const newHeight = animationCanvas.height;
        if (newWidth === 0 || newHeight === 0) {
            return;
        }
    }
    
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.35;
    
    // Clear canvas
    animationCtx.fillStyle = '#1a1a2e';
    animationCtx.fillRect(0, 0, width, height);
    
    const activePlayers = animationPlayers.filter(p => !eliminatedPlayers.includes(p));
    const allPlayers = [...activePlayers, ...eliminatedToShow];
    
    if (allPlayers.length === 0) {
        animationCtx.fillStyle = '#ffffff';
        animationCtx.font = '20px monospace';
        animationCtx.textAlign = 'center';
        animationCtx.fillText('Run a simulation to see animation', centerX, centerY);
        return;
    }
    
    // Arrange all players in circle
    const angleStep = allPlayers.length > 0 ? (2 * Math.PI) / allPlayers.length : 0;
    
    allPlayers.forEach((player, index) => {
        const angle = index * angleStep;
        const isEliminated = eliminatedToShow.includes(player);
        
        // Smooth movement to target position
        const targetX = centerX + radius * Math.cos(angle);
        const targetY = centerY + radius * Math.sin(angle);
        
        if (player.x === 0 && player.y === 0) {
            player.x = targetX;
            player.y = targetY;
        } else {
            player.x += (targetX - player.x) * 0.1;
            player.y += (targetY - player.y) * 0.1;
        }
        
        // Draw player dot
        animationCtx.beginPath();
        animationCtx.arc(player.x, player.y, 8, 0, 2 * Math.PI);
        
        if (isEliminated) {
            // Draw eliminated player in red
            animationCtx.fillStyle = '#ff0000';
        } else {
            animationCtx.fillStyle = strategyColors[player.strategy] || '#ffffff';
        }
        animationCtx.fill();
        
        animationCtx.strokeStyle = '#ffffff';
        animationCtx.lineWidth = 1;
        animationCtx.stroke();
    });
    
    // Draw legend
    drawLegend();
}

/**
 * Calculate which players were eliminated and which are newborns
 */
function calculatePlayerChanges(previousState, currentState) {
    eliminatedPlayers = [];
    newbornPlayers = [];
    
    // Find eliminated players (those in previous but not in current)
    const prevCounts = previousState.strategy_counts;
    const currCounts = currentState.strategy_counts;
    
    // Simplified: track by strategy counts
    // In a real implementation, we'd track individual player IDs
    const prevTotal = previousState.population_size;
    const currTotal = currentState.population_size;
    
    // Mark eliminated if population decreased
    if (prevTotal > currTotal) {
        const eliminatedCount = prevTotal - currTotal;
        // Mark some players as eliminated (simplified)
        for (let i = 0; i < Math.min(eliminatedCount, animationPlayers.length); i++) {
            eliminatedPlayers.push(animationPlayers[i]);
        }
    }
    
    // Mark newborns if population increased
    if (currTotal > prevTotal) {
        const newbornCount = currTotal - prevTotal;
        // New players will be added in setupAnimationPlayers
    }
}

/**
 * Pause animation playback
 */
function pauseAnimationPlayback() {
    animationPlaying = false;
    const playButton = document.getElementById('animation-play-button');
    const pauseButton = document.getElementById('animation-pause-button');
    if (playButton) playButton.style.display = 'inline-block';
    if (pauseButton) pauseButton.style.display = 'none';
    
    if (animationInterval) {
        clearInterval(animationInterval);
        animationInterval = null;
    }
}

/**
 * Setup animation players from state
 */
function setupAnimationPlayers(state) {
    const newPlayers = [];
    let playerId = 0;
    
    Object.entries(state.strategy_counts).forEach(([strategy, count]) => {
        for (let i = 0; i < count; i++) {
            // Check if this is a newborn (population increased)
            const isNewborn = state.population_size > (previousGenerationPlayers.length || 0) && 
                             playerId >= (previousGenerationPlayers.length || 0);
            
            newPlayers.push({
                id: playerId++,
                strategy: strategy,
                angle: 0, // Will be set in draw
                x: 0,
                y: 0,
                targetX: 0,
                targetY: 0,
                isNewborn: isNewborn,
                birthTime: isNewborn ? Date.now() : null
            });
        }
    });
    
    // Track previous generation
    previousGenerationPlayers = [...animationPlayers];
    
    // Shuffle for random pairing
    animationPlayers = newPlayers.sort(() => Math.random() - 0.5);
    
    // Mark new players as newborns
    if (state.population_size > (previousGenerationPlayers.length || 0)) {
        const startIdx = previousGenerationPlayers.length || 0;
        for (let i = startIdx; i < animationPlayers.length; i++) {
            animationPlayers[i].isNewborn = true;
            animationPlayers[i].birthTime = Date.now();
            if (!newbornPlayers.find(p => p.id === animationPlayers[i].id)) {
                newbornPlayers.push(animationPlayers[i]);
            }
        }
    }
}

/**
 * Draw night view (players arranged in circle)
 */
function drawNightView() {
    if (!animationCtx || !animationCanvas) return;
    
    const width = animationCanvas.width;
    const height = animationCanvas.height;
    
    // Check if canvas has valid dimensions
    if (width === 0 || height === 0) {
        // Try to resize and retry
        resizeAnimationCanvas();
        const newWidth = animationCanvas.width;
        const newHeight = animationCanvas.height;
        if (newWidth === 0 || newHeight === 0) {
            return; // Still no valid dimensions
        }
    }
    
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.35;
    
    // Clear canvas
    animationCtx.fillStyle = '#1a1a2e';
    animationCtx.fillRect(0, 0, width, height);
    
    if (animationPlayers.length === 0) {
        animationCtx.fillStyle = '#ffffff';
        animationCtx.font = '20px monospace';
        animationCtx.textAlign = 'center';
        animationCtx.fillText('Run a simulation to see animation', centerX, centerY);
        return;
    }
    
    // Only draw active players (eliminated players are removed, not drawn)
    const activePlayers = animationPlayers.filter(p => !eliminatedPlayers.includes(p));
    const activeAngleStep = activePlayers.length > 0 ? (2 * Math.PI) / activePlayers.length : 0;
    
    activePlayers.forEach((player, index) => {
        const angle = index * activeAngleStep;
        player.angle = angle;
        
        // Smooth movement to target position
        const targetX = centerX + radius * Math.cos(angle);
        const targetY = centerY + radius * Math.sin(angle);
        
        if (player.x === 0 && player.y === 0) {
            // Initial position
            player.x = targetX;
            player.y = targetY;
        } else {
            // Smooth interpolation
            player.x += (targetX - player.x) * 0.1;
            player.y += (targetY - player.y) * 0.1;
        }
        
        player.targetX = targetX;
        player.targetY = targetY;
        
        // Draw player dot
        animationCtx.beginPath();
        animationCtx.arc(player.x, player.y, 8, 0, 2 * Math.PI);
        
        // Check if newborn (show light border)
        const isNewborn = player.isNewborn && player.birthTime && (Date.now() - player.birthTime < 2000);
        
        animationCtx.fillStyle = strategyColors[player.strategy] || '#ffffff';
        animationCtx.fill();
        
        // Draw border - bright for newborns
        if (isNewborn) {
            animationCtx.strokeStyle = '#00ffff';
            animationCtx.lineWidth = 3;
            animationCtx.shadowBlur = 10;
            animationCtx.shadowColor = '#00ffff';
        } else {
            animationCtx.strokeStyle = '#ffffff';
            animationCtx.lineWidth = 1;
            animationCtx.shadowBlur = 0;
        }
        animationCtx.stroke();
        animationCtx.shadowBlur = 0;
    });
    
    // Draw legend
    drawLegend();
    
    // Only continue animation loop if actively playing (not just viewing)
    // For static view, we draw once and stop
    if (animationPlaying && animationState === 'night') {
        requestAnimationFrame(drawNightView);
    }
}

/**
 * Draw day view (paired players move randomly within circle and interact)
 */
function drawDayView() {
    if (!animationCtx || !animationCanvas) return;
    
    const width = animationCanvas.width;
    const height = animationCanvas.height;
    
    // Check if canvas has valid dimensions
    if (width === 0 || height === 0) {
        resizeAnimationCanvas();
        const newWidth = animationCanvas.width;
        const newHeight = animationCanvas.height;
        if (newWidth === 0 || newHeight === 0) {
            return;
        }
    }
    
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.35;
    
    // Clear canvas
    animationCtx.fillStyle = '#1a1a2e';
    animationCtx.fillRect(0, 0, width, height);
    
    const activePlayers = animationPlayers.filter(p => !eliminatedPlayers.includes(p));
    if (activePlayers.length === 0) return;
    
    if (animationPairs.length === 0) {
        // No pairs yet, just draw players
        activePlayers.forEach(player => {
            animationCtx.beginPath();
            animationCtx.arc(player.x || centerX, player.y || centerY, 8, 0, 2 * Math.PI);
            animationCtx.fillStyle = strategyColors[player.strategy] || '#ffffff';
            animationCtx.fill();
            animationCtx.strokeStyle = '#ffffff';
            animationCtx.lineWidth = 1;
            animationCtx.stroke();
        });
        drawLegend();
        return;
    }
    
    // Handle different day phases - update movement only during moving/interacting phases
    // Only update if animation is playing
    if (animationPlaying && (dayPhase === 'moving' || dayPhase === 'interacting')) {
        // Update random movement within circle
        animationPairs.forEach(([p1, p2]) => {
            // Update velocities with random changes
            p1.vx += (Math.random() - 0.5) * 0.2;
            p1.vy += (Math.random() - 0.5) * 0.2;
            p2.vx += (Math.random() - 0.5) * 0.2;
            p2.vy += (Math.random() - 0.5) * 0.2;
            
            // Limit velocity
            const maxVel = 2;
            p1.vx = Math.max(-maxVel, Math.min(maxVel, p1.vx));
            p1.vy = Math.max(-maxVel, Math.min(maxVel, p1.vy));
            p2.vx = Math.max(-maxVel, Math.min(maxVel, p2.vx));
            p2.vy = Math.max(-maxVel, Math.min(maxVel, p2.vy));
            
            // Update positions
            p1.x += p1.vx;
            p1.y += p1.vy;
            p2.x += p2.vx;
            p2.y += p2.vy;
            
            // Keep players within circle
            const dist1 = Math.sqrt((p1.x - centerX) ** 2 + (p1.y - centerY) ** 2);
            const dist2 = Math.sqrt((p2.x - centerX) ** 2 + (p2.y - centerY) ** 2);
            
            if (dist1 > radius) {
                const angle = Math.atan2(p1.y - centerY, p1.x - centerX);
                p1.x = centerX + radius * Math.cos(angle);
                p1.y = centerY + radius * Math.sin(angle);
                p1.vx *= -0.5;
                p1.vy *= -0.5;
            }
            
            if (dist2 > radius) {
                const angle = Math.atan2(p2.y - centerY, p2.x - centerX);
                p2.x = centerX + radius * Math.cos(angle);
                p2.y = centerY + radius * Math.sin(angle);
                p2.vx *= -0.5;
                p2.vy *= -0.5;
            }
            
            // Keep pair together (adjacent)
            const pairDist = Math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2);
            const desiredDist = 20; // Distance between paired players
            
            if (pairDist > desiredDist * 1.5) {
                // Pull them together
                const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
                const midX = (p1.x + p2.x) / 2;
                const midY = (p1.y + p2.y) / 2;
                p1.x = midX - desiredDist * 0.5 * Math.cos(angle);
                p1.y = midY - desiredDist * 0.5 * Math.sin(angle);
                p2.x = midX + desiredDist * 0.5 * Math.cos(angle);
                p2.y = midY + desiredDist * 0.5 * Math.sin(angle);
            }
            
            // Separate pairs from other pairs
            animationPairs.forEach(([otherP1, otherP2]) => {
                if (otherP1 === p1 && otherP2 === p2) return;
                
                const otherMidX = (otherP1.x + otherP2.x) / 2;
                const otherMidY = (otherP1.y + otherP2.y) / 2;
                const thisMidX = (p1.x + p2.x) / 2;
                const thisMidY = (p1.y + p2.y) / 2;
                
                const pairDist = Math.sqrt((thisMidX - otherMidX) ** 2 + (thisMidY - otherMidY) ** 2);
                const minPairDist = 100; // Minimum distance between pairs (increased for better separation)
                
                if (pairDist < minPairDist && pairDist > 0) {
                    const angle = Math.atan2(thisMidY - otherMidY, thisMidX - otherMidX);
                    const pushDist = (minPairDist - pairDist) * 0.3; // Increased push force
                    p1.x += pushDist * Math.cos(angle);
                    p1.y += pushDist * Math.sin(angle);
                    p2.x += pushDist * Math.cos(angle);
                    p2.y += pushDist * Math.sin(angle);
                }
            });
        });
    }
    
    // Draw pairs
    animationPairs.forEach(([p1, p2], pairIndex) => {
        // Check if this is the current encounter
        const isCurrentEncounter = pairIndex === currentEncounterIndex;
        const encounterResult = encounterResults.find(r => 
            (r.pair[0] === p1 && r.pair[1] === p2) || (r.pair[0] === p2 && r.pair[1] === p1));
        
        // Draw connection line (only for current encounter)
        if (isCurrentEncounter && dayPhase === 'interacting') {
            animationCtx.beginPath();
            animationCtx.moveTo(p1.x, p1.y);
            animationCtx.lineTo(p2.x, p2.y);
            animationCtx.strokeStyle = '#333366';
            animationCtx.lineWidth = 2;
            animationCtx.stroke();
        }
        
        // Draw player dots
        [p1, p2].forEach((player) => {
            animationCtx.beginPath();
            animationCtx.arc(player.x, player.y, 8, 0, 2 * Math.PI);
            animationCtx.fillStyle = strategyColors[player.strategy] || '#ffffff';
            animationCtx.fill();
            
            // Determine border color
            let borderColor = '#ffffff';
            let borderWidth = 1;
            
            if (dayPhase === 'showing_result' && encounterResult) {
                if (player === encounterResult.winner) {
                    borderColor = '#00ff00'; // Green for winner
                    borderWidth = 3;
                    animationCtx.shadowBlur = 10;
                    animationCtx.shadowColor = '#00ff00';
                } else if (player === encounterResult.loser) {
                    borderColor = '#ff0000'; // Red for loser
                    borderWidth = 3;
                    animationCtx.shadowBlur = 10;
                    animationCtx.shadowColor = '#ff0000';
                }
            }
            
            animationCtx.strokeStyle = borderColor;
            animationCtx.lineWidth = borderWidth;
            animationCtx.stroke();
            animationCtx.shadowBlur = 0;
        });
    });
    
    // Draw unpaired player (if odd number) - find player not in any pair
    const pairedPlayers = new Set();
    animationPairs.forEach(([p1, p2]) => {
        pairedPlayers.add(p1);
        pairedPlayers.add(p2);
    });
    
    const unpairedPlayers = activePlayers.filter(p => !pairedPlayers.has(p));
    unpairedPlayers.forEach(unpaired => {
        if (!unpaired.x || unpaired.x === 0) {
            unpaired.x = centerX;
            unpaired.y = centerY;
        }
        
        // Keep unpaired player near center but allow some movement
        if (animationPlaying && (dayPhase === 'moving' || dayPhase === 'interacting')) {
            unpaired.vx = (unpaired.vx || 0) + (Math.random() - 0.5) * 0.2;
            unpaired.vy = (unpaired.vy || 0) + (Math.random() - 0.5) * 0.2;
            unpaired.vx = Math.max(-1, Math.min(1, unpaired.vx));
            unpaired.vy = Math.max(-1, Math.min(1, unpaired.vy));
            unpaired.x += unpaired.vx;
            unpaired.y += unpaired.vy;
            
            // Keep within circle
            const dist = Math.sqrt((unpaired.x - centerX) ** 2 + (unpaired.y - centerY) ** 2);
            if (dist > radius * 0.5) {
                const angle = Math.atan2(unpaired.y - centerY, unpaired.x - centerX);
                unpaired.x = centerX + radius * 0.5 * Math.cos(angle);
                unpaired.y = centerY + radius * 0.5 * Math.sin(angle);
                unpaired.vx *= -0.5;
                unpaired.vy *= -0.5;
            }
        }
        
        animationCtx.beginPath();
        animationCtx.arc(unpaired.x, unpaired.y, 8, 0, 2 * Math.PI);
        animationCtx.fillStyle = strategyColors[unpaired.strategy] || '#ffffff';
        animationCtx.fill();
        animationCtx.strokeStyle = '#ffffff';
        animationCtx.lineWidth = 1;
        animationCtx.stroke();
    });
    
    // Draw legend
    drawLegend();
    
    // Continue animation loop during all active phases, but only if playing
    if (animationPlaying && animationState === 'day' && (dayPhase === 'moving' || dayPhase === 'interacting' || 
        dayPhase === 'showing_result' || dayPhase === 'returning')) {
        requestAnimationFrame(drawDayView);
    }
}

/**
 * Draw legend
 */
function drawLegend() {
    const legend = document.getElementById('animation-legend');
    legend.innerHTML = '<div style="color: #00ff00; font-weight: bold; margin-bottom: 10px;">Strategies</div>';
    
    const activePlayers = animationPlayers.filter(p => !eliminatedPlayers.includes(p));
    const strategies = [...new Set(activePlayers.map(p => p.strategy))];
    strategies.forEach(strategy => {
        const item = document.createElement('div');
        item.className = 'legend-item';
        
        const colorBox = document.createElement('div');
        colorBox.className = 'legend-color';
        colorBox.style.backgroundColor = strategyColors[strategy] || '#ffffff';
        
        const label = document.createElement('span');
        label.textContent = strategy;
        label.style.color = '#ffffff';
        
        item.appendChild(colorBox);
        item.appendChild(label);
        legend.appendChild(item);
    });
}

/**
 * Update generation info display
 */
function updateGenerationInfo() {
    const infoElement = document.getElementById('animation-generation-info');
    if (infoElement && currentResults && currentResults.length > 0) {
        const currentGen = currentResults[animationGenerationIndex];
        if (currentGen) {
            infoElement.textContent = `Generation: ${currentGen.generation} | Population: ${currentGen.population_size}`;
        }
    }
}

