using CSV, DataFrames, Random
using Statistics  # Add this for mean function
using Dates

println("Starting Wordle Starter Analysis...")
println("Packages loaded successfully")

# CONFIGURATION SETTINGS
const NUM_TEST_TARGETS = 100  # Number of random targets to test each starter against
const SAVE_INTERVAL = 10      # Save results every N starters
const RANDOM_SEED = 12345     # Seed for reproducible results

# Generate unique filename based on settings
function get_results_filename(prefix::String = "results")
    timestamp = Dates.format(Dates.now(), "yyyy-mm-dd_HH-MM-SS")
    return "$(prefix)_targets$(NUM_TEST_TARGETS)_seed$(RANDOM_SEED)_$(timestamp).csv"
end

# Load words from file
function load_words(filename::String)
    println("Attempting to load words from: $filename")
    
    if !isfile(filename)
        println("ERROR: File not found: $filename")
        println("Current directory: $(pwd())")
        println("Files in current directory:")
        for file in readdir(".")
            println("   - $file")
        end
        error("File not found")
    end
    
    words = String[]
    open(filename, "r") do file
        for line in eachline(file)
            word = strip(uppercase(line))
            if length(word) == 5
                push!(words, word)
            end
        end
    end
    
    println("Successfully loaded $(length(words)) words")
    if length(words) > 0
        println("First few words: $(words[1:min(5, length(words))])")
        println("Last few words: $(words[end-min(4, length(words)-1):end])")
    end
    
    return words
end

# Get Wordle feedback
function get_feedback(guess::String, target::String)
    feedback = fill('B', 5)
    target_chars = collect(target)
    guess_chars = collect(guess)
    
    # First pass: mark greens and remove from target
    for i in 1:5
        if guess_chars[i] == target_chars[i]
            feedback[i] = 'G'
            target_chars[i] = '*'  # Mark as used
            guess_chars[i] = '*'   # Mark as used
        end
    end
    
    # Second pass: mark yellows
    for i in 1:5
        if guess_chars[i] != '*' && guess_chars[i] in target_chars
            feedback[i] = 'Y'
            idx = findfirst(x -> x == guess_chars[i], target_chars)
            target_chars[idx] = '*'  # Mark as used
        end
    end
    
    return String(feedback)
end

# Filter words based on guess and feedback
function filter_words(words::Vector{String}, guess::String, feedback::String)
    valid_words = String[]
    
    for word in words
        if get_feedback(guess, word) == feedback
            push!(valid_words, word)
        end
    end
    
    return valid_words
end

# Calculate letter frequencies in remaining words
function get_letter_frequencies(words::Vector{String})
    freq = Dict{Char, Int}()
    
    for word in words
        for char in Set(word)  # Count each letter once per word
            freq[char] = get(freq, char, 0) + 1
        end
    end
    
    return freq
end

# Score word based on letter frequency
function score_word_frequency(word::String, letter_freq::Dict{Char, Int})
    return sum(get(letter_freq, char, 0) for char in Set(word))
end

# Calculate partitions for minimax evaluation
function calculate_partitions(guess::String, possible_words::Vector{String})
    partitions = Dict{String, Vector{String}}()
    
    for word in possible_words
        feedback = get_feedback(guess, word)
        if !haskey(partitions, feedback)
            partitions[feedback] = String[]
        end
        push!(partitions[feedback], word)
    end
    
    return partitions
end

# Evaluate guess using minimax strategy
function evaluate_guess(guess::String, possible_words::Vector{String})
    partitions = calculate_partitions(guess, possible_words)
    
    is_possible_answer = guess in possible_words
    
    partition_sizes = [length(partition) for partition in values(partitions)]
    max_remaining = isempty(partition_sizes) ? 0 : maximum(partition_sizes)
    avg_remaining = isempty(partition_sizes) ? 0.0 : mean(partition_sizes)
    total_eliminated = length(possible_words) - avg_remaining
    
    return max_remaining, avg_remaining, is_possible_answer, total_eliminated
end

# Choose best word using intelligent strategy
function choose_best_word(possible_words::Vector{String}, all_words::Vector{String}, turn::Int, 
                         known_letters::Set{Char}, excluded_letters::Set{Char}, starter_word::String="")
    
    if length(possible_words) == 1
        return possible_words[1]
    end
    
    words_remaining = length(possible_words)
    
    # Strategy thresholds
    SMALL_SET_THRESHOLD = 2
    MEDIUM_SET_THRESHOLD = 6
    ELIMINATION_THRESHOLD = 15
    LATE_GAME_TURN = 5
    
    # Use specified starter for first turn
    if turn == 1 && !isempty(starter_word)
        return starter_word
    end
    
    letter_freq = get_letter_frequencies(possible_words)
    
    # Special case: 2 words remaining
    if words_remaining == 2
        word1, word2 = possible_words[1], possible_words[2]
        
        # Find distinguishing word
        for word in all_words[1:min(200, length(all_words))]
            if !(word in possible_words)
                feedback1 = get_feedback(word, word1)
                feedback2 = get_feedback(word, word2)
                if feedback1 != feedback2
                    return word
                end
            end
        end
        
        return possible_words[1]  # Fallback
    end
    
    # Select evaluation set based on strategy
    evaluation_set = String[]
    
    if words_remaining > ELIMINATION_THRESHOLD
        # Force elimination mode
        for word in all_words[1:min(800, length(all_words))]
            if !(word in possible_words)
                word_letters = Set(word)
                unexplored_letters = setdiff(word_letters, union(known_letters, excluded_letters))
                if length(unexplored_letters) >= 3
                    push!(evaluation_set, word)
                end
            end
        end
        
        if length(evaluation_set) < 50
            for word in all_words[1:min(800, length(all_words))]
                if !(word in possible_words)
                    word_score = score_word_frequency(word, letter_freq)
                    if word_score > 0
                        push!(evaluation_set, word)
                    end
                end
            end
        end
        
        evaluation_set = evaluation_set[1:min(150, length(evaluation_set))]
        
    elseif words_remaining > MEDIUM_SET_THRESHOLD
        # Medium set: prioritize unexplored letters
        elimination_words = Tuple{Int, String}[]
        
        for word in all_words[1:min(600, length(all_words))]
            if !(word in possible_words)
                word_letters = Set(word)
                unexplored_letters = setdiff(word_letters, union(known_letters, excluded_letters))
                if length(unexplored_letters) >= 2
                    push!(elimination_words, (length(unexplored_letters), word))
                end
            end
        end
        
        sort!(elimination_words, by=x->x[1], rev=true)
        evaluation_set = [word for (_, word) in elimination_words[1:min(100, length(elimination_words))]]
        
    else
        # Small set: focus on answers
        evaluation_set = copy(possible_words)
        if length(evaluation_set) < 50
            for word in all_words[1:min(100, length(all_words))]
                if !(word in evaluation_set)
                    push!(evaluation_set, word)
                end
            end
        end
    end
    
    # Evaluate candidates
    candidates = Tuple{Float64, String, Int, Float64, Bool, Int, Int}[]
    
    for word in evaluation_set
        max_remaining, avg_remaining, is_possible_answer, total_eliminated = evaluate_guess(word, possible_words)
        
        word_letters = Set(word)
        unexplored_letters = setdiff(word_letters, union(known_letters, excluded_letters))
        known_letters_in_word = length(intersect(word_letters, known_letters))
        
        # Scoring system
        base_score = max_remaining
        tie_breaker = avg_remaining / 1000
        
        # Exploration bonus
        exploration_bonus = 0.0
        if !is_possible_answer && words_remaining > MEDIUM_SET_THRESHOLD
            exploration_bonus = -length(unexplored_letters) * 0.5
            known_letter_penalty = known_letters_in_word * 0.3
            exploration_bonus += known_letter_penalty
        end
        
        # Answer vs elimination preference
        answer_bonus = 0.0
        if is_possible_answer
            if words_remaining <= SMALL_SET_THRESHOLD || turn >= LATE_GAME_TURN
                answer_bonus = -1.0
            else
                answer_bonus = 2.0
            end
        else
            if words_remaining > MEDIUM_SET_THRESHOLD
                answer_bonus = -0.5
            end
        end
        
        final_score = base_score + tie_breaker + answer_bonus + exploration_bonus
        
        push!(candidates, (final_score, word, max_remaining, avg_remaining, is_possible_answer, 
                          length(unexplored_letters), known_letters_in_word))
    end
    
    sort!(candidates)
    
    return candidates[1][2]  # Return best word
end

# Solve Wordle for a target word with specified starter
function solve_wordle(target_word::String, word_list::Vector{String}, starter_word::String)
    possible_words = copy(word_list)
    guesses = String[]
    
    # Track knowledge
    known_letters = Set{Char}()
    known_positions = fill(' ', 5)
    excluded_letters = Set{Char}()
    wrong_positions = Dict{Char, Set{Int}}()
    
    for turn in 1:6
        # Choose best word
        guess = choose_best_word(possible_words, word_list, turn, known_letters, excluded_letters, starter_word)
        push!(guesses, guess)
        
        # Get feedback
        feedback = get_feedback(guess, target_word)
        
        # Update knowledge
        for (i, (letter, fb)) in enumerate(zip(guess, feedback))
            if fb == 'G'
                known_positions[i] = letter
                push!(known_letters, letter)
            elseif fb == 'Y'
                push!(known_letters, letter)
                if !haskey(wrong_positions, letter)
                    wrong_positions[letter] = Set{Int}()
                end
                push!(wrong_positions[letter], i)
            else
                if !(letter in known_letters)
                    push!(excluded_letters, letter)
                end
            end
        end
        
        # Check if solved
        if feedback == "GGGGG"
            return guesses, turn
        end
        
        # Filter remaining words
        possible_words = filter_words(possible_words, guess, feedback)
        
        if length(possible_words) == 0
            break  # No valid words remain
        end
    end
    
    return guesses, 7  # Failed to solve
end

# Main analysis function
function analyze_starter_words()
    println("\nStarting main analysis function...")
    println("CONFIGURATION:")
    println("  Test targets per starter: $NUM_TEST_TARGETS")
    println("  Random seed: $RANDOM_SEED")
    println("  Save interval: every $SAVE_INTERVAL starters")
    
    println("\nLoading words...")
    words = load_words("T:/WordleCalculator/src/wordle.txt")
    println("Words loaded successfully: $(length(words)) total")
    
    if length(words) == 0
        println("ERROR: No words loaded!")
        return nothing
    end
    
    # Validate NUM_TEST_TARGETS
    if NUM_TEST_TARGETS > length(words)
        println("WARNING: NUM_TEST_TARGETS ($NUM_TEST_TARGETS) is larger than available words ($(length(words)))")
        println("Using all $(length(words)) words as targets")
        actual_test_targets = length(words)
    else
        actual_test_targets = NUM_TEST_TARGETS
    end
    
    # Test the solver with a quick example
    println("\nTesting solver functionality...")
    test_target = words[1]
    test_starter = words[2]
    println("   Testing with target: $test_target, starter: $test_starter")
    test_guesses, test_tries = solve_wordle(test_target, words, test_starter)
    println("   Solver test completed: $test_tries tries, guesses: $test_guesses")
    
    # Initialize results DataFrame
    println("\nInitializing results DataFrame...")
    results_df = DataFrame(
        starter_word = String[],
        failed = Int[],
        tries_6 = Int[],
        tries_5 = Int[],
        tries_4 = Int[],
        tries_3 = Int[],
        tries_2 = Int[],
        tries_1 = Int[],
        total_games = Int[],
        success_rate = Float64[],
        avg_tries = Float64[]
    )
    println("DataFrame initialized")
    
    # Generate unique filenames
    intermediate_filename = get_results_filename("results_intermediate")
    final_filename = get_results_filename("results_final")
    println("Results will be saved as:")
    println("  Intermediate: $intermediate_filename")
    println("  Final: $final_filename")
    
    # Test ALL words as starters
    starter_candidates = words  # Test ALL words
    total_starters = length(starter_candidates)
    println("\nTesting ALL $(total_starters) starter words against $actual_test_targets random targets each")
    println("Total games to be played: $(total_starters * actual_test_targets)")
    
    # Pre-generate random targets to use for all starters (for consistency)
    Random.seed!(RANDOM_SEED)  # Set seed for reproducible results
    test_targets = shuffle(words)[1:actual_test_targets]
    println("Selected $actual_test_targets random target words for testing")
    
    for (starter_idx, starter_word) in enumerate(starter_candidates)
        println("\n" * "="^60)
        println("Testing starter word: $starter_word ($(starter_idx)/$total_starters)")
        println("Progress: $(round(starter_idx/total_starters*100, digits=1))%")
        println("="^60)
        
        # Initialize counts for this starter
        failed = 0
        tries_counts = [0, 0, 0, 0, 0, 0]  # tries_1 through tries_6
        total_successful_tries = 0
        
        # Test against the random target words
        for (target_idx, target_word) in enumerate(test_targets)
            guesses, tries = solve_wordle(target_word, words, starter_word)
            
            if tries > 6
                failed += 1
            else
                tries_counts[tries] += 1
                total_successful_tries += tries
            end
        end
        
        # Calculate statistics
        total_games = length(test_targets)
        successful_games = total_games - failed
        success_rate = successful_games / total_games * 100
        avg_tries = successful_games > 0 ? total_successful_tries / successful_games : 0.0
        
        println("Results calculated:")
        println("   Total games: $total_games")
        println("   Successful: $successful_games")
        println("   Failed: $failed")
        println("   Success rate: $(round(success_rate, digits=1))%")
        println("   Average tries: $(round(avg_tries, digits=2))")
        
        # Add results to DataFrame
        push!(results_df, (
            starter_word,
            failed,
            tries_counts[6],  # 6 tries
            tries_counts[5],  # 5 tries
            tries_counts[4],  # 4 tries
            tries_counts[3],  # 3 tries
            tries_counts[2],  # 2 tries
            tries_counts[1],  # 1 try
            total_games,
            success_rate,
            avg_tries
        ))
        
        # Save intermediate results every SAVE_INTERVAL starters
        if starter_idx % SAVE_INTERVAL == 0 || starter_idx == total_starters
            println("Saving intermediate results...")
            try
                # Sort current results before saving
                sorted_df = sort(results_df, [:success_rate, :avg_tries], rev=[true, false])
                CSV.write(intermediate_filename, sorted_df)
                println("Results saved to $intermediate_filename ($(nrow(sorted_df)) rows)")
                
                # Show current top 5
                println("Current top 5 starters:")
                for i in 1:min(5, nrow(sorted_df))
                    row = sorted_df[i, :]
                    println("  $(i). $(row.starter_word): $(round(row.success_rate, digits=1))% success, $(round(row.avg_tries, digits=2)) avg tries")
                end
            catch e
                println("Error saving results: $e")
            end
        end
        
        println("Distribution: 1:$(tries_counts[1]), 2:$(tries_counts[2]), 3:$(tries_counts[3]), 4:$(tries_counts[4]), 5:$(tries_counts[5]), 6:$(tries_counts[6]), Failed:$failed")
    end
    
    # Sort by success rate and average tries
    println("\nSorting final results...")
    sort!(results_df, [:success_rate, :avg_tries], rev=[true, false])
    
    # Save final results
    println("Saving final results...")
    try
        CSV.write(final_filename, results_df)
        println("Final results saved successfully to $final_filename")
    catch e
        println("Error saving final results: $e")
    end
    
    println("\n" * "="^60)
    println("ANALYSIS COMPLETE!")
    println("="^60)
    println("Configuration used:")
    println("  Test targets: $actual_test_targets")
    println("  Random seed: $RANDOM_SEED")
    println("  Total starters tested: $(nrow(results_df))")
    println("  Total games played: $(nrow(results_df) * actual_test_targets)")
    
    println("\nTop 20 starter words:")
    for i in 1:min(20, nrow(results_df))
        row = results_df[i, :]
        println("$(i). $(row.starter_word): $(round(row.success_rate, digits=1))% success, $(round(row.avg_tries, digits=2)) avg tries")
    end
    
    println("\nResults saved to: $final_filename")
    
    return results_df
end

# Run the analysis
if abspath(PROGRAM_FILE) == @__FILE__
    println("Script started directly, running analysis...")
    try
        results = analyze_starter_words()
        println("Analysis completed successfully!")
    catch e
        println("ERROR during analysis: $e")
        println("Stack trace:")
        showerror(stdout, e, catch_backtrace())
    end
else
    println("Script loaded as module")
end