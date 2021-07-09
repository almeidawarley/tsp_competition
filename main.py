import env
import uuid as ui
import numpy as np
import cplex as cp
import time as tm
import sys

def name_x(i, j):
    """
    Name variable x for arc (i, j)
    """

    return 'x_' + str(i) + '_' + str(j)

def name_t(i):
    """
    Name variable t for node i
    """

    return 't_' + str(i)

def retrieve_coefficient(instance, i, j):
    """
    Retrieve coefficient for arc (i, j)
    """

    # If it is a self loop, set coefficient to zero
    if i == j:
        return 0
    # Otherwise, set coefficient to the reward
    else:
        return instance.rewards[j - 1]

def create_variables(instance, solver):
    """
    Create decision variables for the model
    """

    # Create auxiliary vectors
    names = []
    coefficients = []
    types = ['B' for i in instance.nodes for j in instance.nodes]
    uppers = [1 for i in instance.nodes for j in instance.nodes]
    lowers = [0 for i in instance.nodes for j in instance.nodes]

    # Create variable x per arc (i, j)
    for i in instance.nodes:
        for j in instance.nodes:
            names.append(name_x(i, j))
            coefficients.append(retrieve_coefficient(instance, i, j))

    solver.variables.add(obj = coefficients, ub = uppers, lb = lowers, types = types, names = names)

    # Create auxiliary vectors
    M = instance.n_nodes
    names = []
    coefficients = []
    types = ['C' for i in instance.nodes]
    uppers = [M for i in instance.nodes]
    lowers = [0 for i in instance.nodes]

    # Create variable t per node i
    for i in instance.nodes:
        names.append(name_t(i))
        coefficients.append(0)

    solver.variables.add(obj = coefficients, ub = uppers, lb = lowers, types = types, names = names)

def create_flow_constraint(instance, solver):
    """
    Flow constraint at node
    """

    # Create auxiliary vectors
    rows = []
    senses = []
    rhs = []
    names = []

    # Create flow constraint per node i
    for i in instance.nodes:
        senses.append('E')
        names.append('flw_' + str(i))
        rhs.append(0)
        coefficients = []
        variables = []
        for k in instance.nodes:
            # Ignore self loops
            if i != k:
                coefficients.append(1)
                variables.append(name_x(i, k))
                coefficients.append(-1)
                variables.append(name_x(k, i))
        rows.append([variables,coefficients])

    solver.linear_constraints.add(lin_expr = rows, senses = senses, rhs = rhs, names = names)

def create_depart_constraint(instance, solver):
    """
    Depart constraint from node
    """

    # Create auxiliary vectors
    rows = []
    senses = []
    rhs = []
    names = []

    # Create depart constraint per node i
    for i in instance.nodes:
        senses.append('L')
        names.append('dpt_' + str(i))
        rhs.append(1)
        coefficients = []
        variables = []
        for k in instance.nodes:
            coefficients.append(1)
            variables.append(name_x(i, k))
        rows.append([variables,coefficients])

    solver.linear_constraints.add(lin_expr = rows, senses = senses, rhs = rhs, names = names)

def create_arrival_constraint(instance, solver):
    """
    Arrival constraint at node
    """

    # Create auxiliary vectors
    rows = []
    senses = []
    rhs = []
    names = []

    # Create arrival constraint per node i
    for i in instance.nodes:
        senses.append('L')
        names.append('arr_' + str(i))
        rhs.append(1)
        coefficients = []
        variables = []
        for k in instance.nodes:
            coefficients.append(1)
            variables.append(name_x(k, i))
        rows.append([variables,coefficients])

    solver.linear_constraints.add(lin_expr = rows, senses = senses, rhs = rhs, names = names)

def create_start_constraint(instance, solver):
    """
    Start constraint at depot
    """

    # Create auxiliary vectors
    rows = []
    senses = []
    rhs = []
    names = []

    # Create start constraint at depot
    senses.append('E')
    names.append('str')
    rhs.append(1)
    coefficients = []
    variables = []
    for k in instance.nodes:
        coefficients.append(1)
        variables.append(name_x(1,k))
    rows.append([variables,coefficients])

    solver.linear_constraints.add(lin_expr = rows, senses = senses, rhs = rhs, names = names)

def create_end_constraint(instance, solver):
    """
    End constraint at depot
    """

    # Create auxiliary vectors
    rows = []
    senses = []
    rhs = []
    names = []

    # Create end constraint at depot
    senses.append('E')
    names.append('dne')
    rhs.append(1)
    coefficients = []
    variables = []
    for k in instance.nodes:
        coefficients.append(1)
        variables.append(name_x(k,1))
    rows.append([variables,coefficients])

    solver.linear_constraints.add(lin_expr = rows, senses = senses, rhs = rhs, names = names)

def create_order_constraint(instance, solver):
    """
    Order constraint for arc
    """

    # Create auxiliary vectors
    rows = []
    senses = []
    rhs = []
    names = []

    M = instance.n_nodes

    # Create order constraint per arc (i, j)
    for i in instance.nodes:
        for j in instance.nodes:
            # Ignore self loops
            # Ignore return to depot
            if i != j and j != 1:
                senses.append('G')
                names.append('ord_' + str(i) + '_' + str(j))
                rhs.append(1 - M)
                coefficients = []
                variables = []
                coefficients.append(1)
                variables.append(name_t(j))
                coefficients.append(-1)
                variables.append(name_t(i))
                coefficients.append(-1 *  M)
                variables.append(name_x(i, j))
                rows.append([variables,coefficients])

    solver.linear_constraints.add(lin_expr = rows, senses = senses, rhs = rhs, names = names)

def create_size_constraint(instance, solver, size):
    """
    Tour size constraint
    """

    # Create auxiliary vectors
    rows = []
    senses = []
    rhs = []
    names = []

    # Create tour size constraint
    senses.append('L')
    names.append('siz')
    rhs.append(size)
    coefficients = []
    variables = []
    for i in instance.nodes:
        for j in instance.nodes:
            coefficients.append(1)
            variables.append(name_x(i, j))
    rows.append([variables,coefficients])

    solver.linear_constraints.add(lin_expr = rows, senses = senses, rhs = rhs, names = names)

def cut_infeasible(solver, solution, identifier):
    """
    Cut an infeasible solution
    """

    # Create auxiliary vectors
    rows = []
    senses = []
    rhs = []
    names = []

    # Create infeasible solution cut
    senses.append('L')
    names.append('inf_' + str(identifier))
    coefficients = []
    variables = []
    index = 0
    while solution[index + 1] != 1:
        # Until the depot appears, add arc (i,j) to the cut
        coefficients.append(1)
        variables.append(name_x(solution[index], solution[index + 1]))
        index += 1
    rhs.append(index - 1)
    rows.append([variables,coefficients])

    solver.linear_constraints.add(lin_expr = rows, senses = senses, rhs = rhs, names = names)

def cut_feasible(solver, solution, identifier):
    """
    Cut a feasible solution
    """

    # Create auxiliary vectors
    rows = []
    senses = []
    rhs = []
    names = []

    # Create feasible solution cut    
    senses.append('L')
    names.append('fea_' + str(identifier))
    coefficients = []
    variables = []
    index = 0
    while solution[index + 1] != 1:
        # Until the depot appears, add arc (i,j) to the cut
        coefficients.append(1)
        variables.append(name_x(solution[index], solution[index + 1]))
        index += 1
    # Add return to the depot to the cut
    coefficients.append(1)
    variables.append(name_x(solution[index], solution[index + 1]))
    rhs.append(index)
    rows.append([variables,coefficients])

    solver.linear_constraints.add(lin_expr = rows, senses = senses, rhs = rhs, names = names)

def cut_impossible(instance, solver):
    """
    Cut (certainly) impossible nodes
    """

    # Create auxiliary vectors
    rows = []
    senses = []
    rhs = []
    names = []

    # Find impossible nodes
    impossible = []
    for i in instance.nodes:
        if i != 1:
            solution = [1, i, 1]
            for j in instance.nodes:
                if j not in solution:
                    solution.append(j)
            objective, _, _, _ = check_performance(instance, solution)  
            if objective <= 0:
                impossible.append(i)

    # Create unreachable cut
    senses.append('L')
    names.append('imp')
    rhs.append(0)
    coefficients = []
    variables = []
    for i in impossible:
        for k in instance.nodes:
            variable = name_x(i, k)
            if variable not in variables:
                variables.append(variable)
                coefficients.append(1)
            variable = name_x(k, i)
            if variable not in variables:
                variables.append(variable)
                coefficients.append(1)
    rows.append([variables,coefficients])

    solver.linear_constraints.add(lin_expr = rows, senses = senses, rhs = rhs, names = names)

    print('There are {} impossible nodes: {}'.format(len(impossible), impossible))

    return impossible

def cut_unreachable(instance, solver):
    """
    Cut (likely) unreachable arcs
    """

    # Create auxiliary vectors
    rows = []
    senses = []
    rhs = []
    names = []

    unreachable = []
    # Create unreachable cut
    senses.append('L')
    names.append('unr')
    rhs.append(0)
    coefficients = []
    variables = []
    for i in instance.nodes:
        for j in instance.nodes:
            # If leaving the earliest from node i cannot reach node j in time, cut arc (i, j)
            if instance.opening[i-1] + instance.times[i-1][j-1] > instance.closing[j-1]:
                variables.append(name_x(i, j))
                coefficients.append(1)
                unreachable.append([i, j])
    rows.append([variables,coefficients])

    solver.linear_constraints.add(lin_expr = rows, senses = senses, rhs = rhs, names = names)

    # print('There are {} unreachable arcs: {}'.format(len(unreachable), unreachable))

    return unreachable

def relax_unreachable(instance, solver, step):
    """
    Relax unreachable cut according to a step
    """

    rhs = solver.linear_constraints.get_rhs('unr')
    solver.linear_constraints.set_rhs('unr', rhs + step)


def build_model(instance):
    """
    Build the model for the tracker approach
    """ 

    # Create solver instance
    solver = cp.Cplex()

    # Set solver parameters
    solver.objective.set_sense(solver.objective.sense.maximize)
    # solver.parameters.mip.tolerances.mipgap.set(0.1)
    # solver.parameters.threads.set(1)
    solver.set_results_stream(None)
    solver.set_log_stream(None)

    # Create variables and constraints
    create_variables(instance, solver)
    create_flow_constraint(instance, solver)
    create_depart_constraint(instance, solver)
    create_arrival_constraint(instance, solver)
    create_start_constraint(instance, solver)
    create_end_constraint(instance, solver)
    create_order_constraint(instance, solver)
    
    # Create impossible cuts
    impossible = cut_impossible(instance, solver)
    # Create unreachable cuts
    unreachable = cut_unreachable(instance, solver)

    return solver, len(impossible)

def run_model(instance, solver, size, path = 'dummy.lp'):
    """
    Run the model for the tracker approach
    """ 

    # Add tour size constraint
    create_size_constraint(instance, solver, size)

    try:
        # Run the solver
        solver.solve()
        # Retrieve the solution
        objective = solver.solution.get_objective_value()
        solution = {variable: value for (variable, value) in 
            zip(solver.variables.get_names(), solver.solution.get_values())}
    except:
        return -1 * np.inf, {}    

    # Export the model
    solver.write(path)

    # Remove tour size constraint
    solver.linear_constraints.delete('siz')

    objective = round(objective, 10)

    return objective, solution


def check_performance(instance, solution, simulations = 10 ** 4, flag = False):
    """
    Check the performance of a solution
    """

    # Create average variables
    avg_time = 0
    avg_reward = 0
    avg_penalty = 0
    percentage = 0

    counter = 0
    while counter < simulations:

        # Call black-box simulator
        time, reward, penalty, feasible = instance.check_solution(solution)

        # Update average variables
        avg_time += time
        avg_reward += reward
        avg_penalty += penalty
        percentage += 1 if feasible else 0

        counter += 1

    avg_time /= simulations
    avg_reward /= simulations
    avg_penalty /= simulations
    percentage /= simulations
    avg_objective = avg_reward + avg_penalty

    # Print relevant information
    if flag:
        print('Solution: ', solution)
        print('Simulations: ', simulations)
        print('Objective: ', avg_objective)
        print('Time: ', avg_time)
        print('Reward: ', avg_reward)
        print('Penalty: ', avg_penalty)
        print('Percentage: ', percentage)

    avg_objective = round(avg_objective, 10)
    avg_reward = round(avg_reward, 10)
    avg_penalty = round(avg_penalty, 10)

    return avg_objective, avg_reward, avg_penalty, percentage


def format_solution(instance, solution):
    """
    Format solution form the model
    """

    # Create auxiliary dictionary
    temporary = {}
    for variable, value in solution.items():
        if value > 0.1 and 'x' in variable:
            _, i, j = variable.split('_')
            i = int(i)
            j = int(j)
            temporary[i] = j

    # Parse auxiliary dictionary
    formatted = []
    formatted.append(1)
    index = 1
    while temporary[index] != 1:
        formatted.append(temporary[index])
        index = temporary[index]
    formatted.append(1)

    # Add remaining nodes to the solution
    for i in instance.nodes:
        if i not in formatted:
            formatted.append(i)

    return formatted

def adapt_coefficients(instance, solver, history, solution, penalty):
    """
    Adapt coefficients based on historical data
    """

    # Create auxiliary vectors
    updates = []

    # Parse arcs in the solution
    arcs = retrieve_arcs(solution)
    for i, j in arcs:
        history[i][j]['weights'] += penalty / len(arcs)
        history[i][j]['occurrences'] += 1
        if history[i][j]['weights'] < 0:
            coefficient = retrieve_coefficient(instance, i, j)
            coefficient += history[i][j]['weights'] / history[i][j]['occurrences']
            variable = name_x(i, j)
            updates.append((variable, coefficient))
    
    solver.objective.set_linear(updates)

def calculate_bound(instance, solver, size):
    """
    Calculate bound for a tour size
    """

    variables = solver.variables.get_names()
    coefficients = solver.objective.get_linear()

    # Restore coefficients to standard values
    updates = []
    for i in instance.nodes:
        for j in instance.nodes:
            updates.append((name_x(i,j), retrieve_coefficient(instance, i, j)))

    solver.objective.set_linear(updates)

    # Retrieve a bound value
    bound, _ = run_model(instance, solver, size, 'bound.lp')

    # Restore coefficients to updated values
    updates = []
    for index, _ in enumerate(variables):
        updates.append((variables[index], coefficients[index]))

    solver.objective.set_linear(updates)
    
    bound = round(bound, 10)

    return bound


def retrieve_arcs(solution):
    """
    Retrieve a list of arcs from a solution
    """

    arcs = []
    # Parse solution until the depot appears
    index = 0
    while solution[index + 1] != 1:
        # Append current arc accordingly
        arcs.append([solution[index], solution[index + 1]])
        index += 1
    # Append final arc to the depot
    arcs.append([solution[index],solution[index + 1]])

    return arcs


def tracker_approach(instance, iterations = 10 ** 3, threshold = 0.8, tolerance = 0.05, simulations = 100, factor = 1):
    """
    Run tracker approach
    """

    assert factor <= 1 and factor >= -1

    # Global variables
    best_solution = []
    best_objective = -1 * np.inf

    # Estimate travel times
    if factor < 0:
        weights = np.random.rand(instance.n_nodes, instance.n_nodes)
    else:
        weights = factor
        
    instance.times = weights * instance.adj

    # Build the model
    solver, blocked = build_model(instance)

    # Historical data    
    history = {}
    for i in instance.nodes:
        history[i] = {}
        for j in instance.nodes:
            history[i][j] = {}
            history[i][j]['weights'] = 0
            history[i][j]['occurrences'] = 0

    # Iterative variables
    size = 2
    counter = 0
    feasible = True
    # Maximum size of the tour
    maximum = instance.n_nodes + 1
    # Frontier size of the tour
    frontier = maximum - blocked

    # Calculate initial bound
    bound = calculate_bound(instance, solver, size)

    # Save start time
    start = tm.time()

    # Iterate until (a) maximum number of iterations, (b) the gap has been closed, (c) the model is no longer feasible
    while counter < iterations and best_objective < bound and feasible:

        # Obtain solution from the model
        approx, solution = run_model(instance, solver, size, 'model.lp')
        #print('Raw solution: ', solution)

        feasible = len(solution) != 0

        # Keep running if the model remains feasible
        if feasible:

            # Format solution in an understandable manner
            solution = format_solution(instance, solution)
            # print('Formatted solution: ', solution)
            
            # Check solution performance
            objective, reward, penalty, percentage = check_performance(instance, solution, simulations)
            
            # Store current solution if it is the best one yet
            if objective >= best_objective:
                best_solution = solution
                best_objective = objective
            
            # If the solution is infeasible most of the time, cut infeasible solution
            if percentage < threshold:
            # if objective < best_objective / 2:
                # print('Solution infeasible')
                cut_infeasible(solver, solution, counter)
            # Otherwise, cut feasible solution because it has been visited already
            else:
                # print('Solution feasible')
                cut_feasible(solver, solution, counter)
            
            # Adapt coefficients based on historical data
            adapt_coefficients(instance, solver, history, solution, penalty)

            # Calculate gap based on the current solution
            gap = (bound - best_objective) / bound
            if gap < tolerance and size < frontier:
                size += 1
                # Calculate current bound
                bound = calculate_bound(instance, solver, size)
            else:
                size += 0

            # Print information about the current iteration
            counter += 1
            print('Approximate objective value for candidate solution at iteration #{}: {}'
                .format(counter, approx))
            print('Candidate solution at iteration #{}: {} [Objective: {}, Size: {}, Bound: {}]'
                .format(counter, solution, objective, size, bound))
            print('Superior solution at iteration #{}: {} [Objective: {}, Size: {}, Bound: {}]'
                .format(counter, best_solution, best_objective, size, bound))
        
        # End algorithm if the model is no longer feasible
        else:
            print('The model is no longer feasible due to the tracked information')

    # Save end time
    end = tm.time()

    # Export solution to .out file
    path = export_solution(best_solution)

    # Performance summary
    print('> Arguments:')
    print('| Iterations: {}'.format(iterations))
    print('| Simulations: {}'.format(simulations))
    print('| Threshold: {}'.format(threshold))
    print('| Tolerance: {}'.format(tolerance))
    print('| Factor: {}'.format(factor))
    print('> Parameters:')
    print('| Feasible: {}'.format(feasible))
    print('| Counter: {}'.format(counter))
    print('| Size: {}'.format(size))
    print('| Maximum: {}'.format(maximum))
    print('| Frontier: {}'.format(frontier))
    print('> Results:')
    print('| Best objective: {}'.format(best_objective))
    print('| Best solution: {}'.format(best_solution))
    print('| Total time: {}'.format(end - start))
    print('| Solution file: {}'.format(path))

    return best_solution

def export_solution(solution):
    """
    Export solution to .out file
    """

    # Create unique identifier for .out file
    name = str(ui.uuid4())[0:8] + '.out'
    # Write solution information to .out file
    with open('solutions/{}'.format(name), 'w') as output:
        for node in solution:
            output.write('{}\n'.format(node))
    
    return name

def load_instance(identifier):
    """
    Load instance from file
    """

    instance = env.Env(from_file = True,  
        x_path = 'data/valid/instances/{}.csv'.format(identifier), 
        adj_path = 'data/valid/adjs/adj-{}.csv'.format(identifier))

    return instance

def load_validation():
    """
    Load validation instance
    """

    instance = env.Env(55, seed = 3119615)

    return instance

def load_competition():
    """
    Load competition instance
    """

    instance = env.Env(65, seed = 6537855)
    
    return instance

def adjust_instance(instance):
    """
    Adjust instance
    """

    instance.nodes = list(range(1, instance.n_nodes + 1))
    instance.rewards = instance.x[:, -2]
    instance.maximum = instance.x[:, -1][1]
    instance.opening = instance.x[:, -4]
    instance.closing = instance.x[:, -3]

    return instance

if __name__ == "__main__":

    if len(sys.argv) > 1:
        instance = load_instance(sys.argv[1])
    else:
        # instance = load_validation()
        instance = load_competition()
    instance = adjust_instance(instance)
    solution = tracker_approach(instance, 
        iterations = 10 ** 3, 
        threshold = 0.8, 
        tolerance = 0.1, # 0.05 
        simulations = 10 ** 2, #10 ** 3, 
        factor = 1)