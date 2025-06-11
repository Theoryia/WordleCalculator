import random
from collections import defaultdict, Counter
from typing import List, Tuple, Set

def load_words(filename: str) -> List[str]:
    """Load 5-letter words from text file."""
    with open(filename, 'r') as f:
        return [word.strip().upper() for word in f if len(word.strip()) == 5]

def get_feedback(guess: str, target: str) -> str:
    """
    Get Wordle feedback for a guess.
    Returns string of G (green), Y (yellow), B (black/gray)
    """
    feedback = ['B'] * 5
    target_chars = list(target)
    guess_chars = list(guess)
    
    # First pass: mark greens and remove from target
    for i in range(5):
        if guess_chars[i] == target_chars[i]:
            feedback[i] = 'G'
            target_chars[i] = None
            guess_chars[i] = None
    
    # Second pass: mark yellows
    for i in range(5):
        if guess_chars[i] and guess_chars[i] in target_chars:
            feedback[i] = 'Y'
            target_chars[target_chars.index(guess_chars[i])] = None
    
    return ''.join(feedback)

def filter_words(words: List[str], guess: str, feedback: str) -> List[str]:
    """Filter word list based on guess and feedback."""
    valid_words = []
    
    for word in words:
        if get_feedback(guess, word) == feedback:
            valid_words.append(word)
    
    return valid_words

def calculate_partitions(guess: str, possible_words: List[str]) -> dict:
    """Calculate how the guess would partition the remaining words."""
    partitions = defaultdict(list)
    
    for word in possible_words:
        feedback = get_feedback(guess, word)
        partitions[feedback].append(word)
    
    return partitions

def evaluate_guess(guess: str, possible_words: List[str], all_words: List[str]) -> Tuple[int, float, bool, int]:
    """
    Evaluate a guess using minimax strategy.
    Returns: (max_remaining, avg_remaining, is_possible_answer, total_eliminated)
    """
    partitions = calculate_partitions(guess, possible_words)
    
    # If this guess could be the answer
    is_possible_answer = guess in possible_words
    
    # Calculate worst case (max remaining) and average case
    partition_sizes = [len(partition) for partition in partitions.values()]
    max_remaining = max(partition_sizes) if partition_sizes else 0
    avg_remaining = sum(partition_sizes) / len(partition_sizes) if partition_sizes else 0
    
    # Calculate total words that would be eliminated in average case
    total_eliminated = len(possible_words) - avg_remaining
    
    return max_remaining, avg_remaining, is_possible_answer, total_eliminated

def get_letter_frequencies(words: List[str]) -> Counter:
    """Get frequency of letters in remaining words."""
    letter_freq = Counter()
    for word in words:
        for char in set(word):  # Count each letter once per word
            letter_freq[char] += 1
    return letter_freq

def score_word_frequency(word: str, letter_freq: Counter) -> int:
    """Score word based on letter frequency in remaining words."""
    return sum(letter_freq[char] for char in set(word))

def find_best_distinguishing_word(possible_words: List[str], all_words: List[str], known_letters: set, excluded_letters: set) -> str:
    """
    Find the best word to distinguish between remaining possibilities.
    Looks for words that can eliminate the most possibilities with one guess.
    """
    if len(possible_words) <= 1:
        return possible_words[0] if possible_words else None
    
    print(f"Finding best distinguishing word for {len(possible_words)} possibilities...")
    if len(possible_words) <= 10:
        print(f"Remaining words: {', '.join(possible_words)}")
    
    best_word = None
    best_score = float('inf')
    best_info = None
    
    # Evaluate elimination candidates (non-answers)
    evaluation_candidates = []
    
    # First, try words that aren't possible answers
    for word in all_words[:500]:  # Check more candidates
        if word not in possible_words:  # Must not be a possible answer
            evaluation_candidates.append(word)
    
    # If we have very few possibilities, also consider the answers themselves
    if len(possible_words) <= 3:
        evaluation_candidates.extend(possible_words)
    
    print(f"Evaluating {len(evaluation_candidates)} distinguishing candidates...")
    
    for word in evaluation_candidates:
        # Calculate how this word would partition the remaining possibilities
        partitions = defaultdict(list)
        
        for possible_word in possible_words:
            feedback = get_feedback(word, possible_word)
            partitions[feedback].append(possible_word)
        
        # Calculate elimination effectiveness
        partition_sizes = [len(partition) for partition in partitions.values()]
        max_remaining = max(partition_sizes) if partition_sizes else 0
        avg_remaining = sum(partition_sizes) / len(partition_sizes) if partition_sizes else 0
        
        # Bonus for exploring new letters
        word_letters = set(word)
        unexplored_letters = word_letters - known_letters - excluded_letters
        exploration_bonus = len(unexplored_letters) * 0.1
        
        # Penalty for reusing excluded letters (they give no info)
        excluded_penalty = len(word_letters & excluded_letters) * 0.5
        
        # Score: prioritize minimizing worst case, then average case
        score = max_remaining + (avg_remaining / 1000) - exploration_bonus + excluded_penalty
        
        if score < best_score:
            best_score = score
            best_word = word
            best_info = {
                'max_remaining': max_remaining,
                'avg_remaining': avg_remaining,
                'partitions': len(partitions),
                'unexplored': len(unexplored_letters),
                'excluded_used': len(word_letters & excluded_letters)
            }
    
    if best_word and best_info:
        print(f"Best distinguishing word: {best_word}")
        print(f"  Max remaining: {best_info['max_remaining']}")
        print(f"  Avg remaining: {best_info['avg_remaining']:.1f}")
        print(f"  Creates {best_info['partitions']} partitions")
        print(f"  Tests {best_info['unexplored']} new letters")
        
        return best_word
    
    # Fallback to first possibility
    return possible_words[0]

def choose_best_word(possible_words: List[str], all_words: List[str], turn: int, known_letters: set = None, excluded_letters: set = None) -> str:
    """
    Choose the best word using intelligent minimax strategy.
    Balances between elimination and going for the answer.
    """
    if len(possible_words) == 1:
        return possible_words[0]
    
    # Initialize knowledge sets if not provided
    if known_letters is None:
        known_letters = set()
    if excluded_letters is None:
        excluded_letters = set()
    
    # Strategy parameters based on game state
    words_remaining = len(possible_words)
    
    # IMPROVED Decision thresholds - much more aggressive elimination
    SMALL_SET_THRESHOLD = 2   # Only go for answers when 2 or fewer remain
    MEDIUM_SET_THRESHOLD = 6  # Special handling for medium sets
    ELIMINATION_THRESHOLD = 15  # Force elimination mode above this
    LATE_GAME_TURN = 5  # Later threshold for late game
    
    print(f"Evaluating candidates... (words remaining: {words_remaining})")
    
    # Use proven starters for first turn
    if turn == 1:
        proven_starters = ["COURT"]
        best_starter = None
        for starter in proven_starters:
            if starter in all_words:
                best_starter = starter
                break
        
        if best_starter:
            print(f"Using proven starter word: {best_starter}")
            return best_starter
        else:
            print("Using fallback starter: ADIEU")
            return "ADIEU"
    
    # IMPROVED: Use smarter distinguishing logic for small sets
    if words_remaining <= 10:
        print("Using specialized distinguishing word search...")
        return find_best_distinguishing_word(possible_words, all_words, known_letters, excluded_letters)
    
    # SPECIAL CASE: When we have exactly 2 words, find a distinguishing word
    if words_remaining == 2:
        word1, word2 = possible_words[0], possible_words[1]
        
        print(f"Two words remaining: {word1} vs {word2}")
        
        # Find the first differing position
        diff_positions = []
        diff_letters = set()
        for i in range(5):
            if word1[i] != word2[i]:
                diff_positions.append(i)
                diff_letters.add(word1[i])
                diff_letters.add(word2[i])
        
        print(f"Different positions: {diff_positions}")
        print(f"Different letters: {sorted(diff_letters)}")
        
        if diff_positions:
            best_distinguisher = None
            best_score = float('inf')
            
            # Look for a word that tests the differing letters
            for word in all_words[:300]:  # Check more words
                if word not in possible_words:  # Don't guess an answer
                    # Check if this word helps distinguish
                    feedback1 = get_feedback(word, word1)
                    feedback2 = get_feedback(word, word2)
                    if feedback1 != feedback2:  # This word will give different feedback
                        # Score based on how many new letters it tests
                        word_letters = set(word)
                        unexplored_letters = word_letters - known_letters - excluded_letters
                        new_letter_bonus = len(unexplored_letters)
                        
                        # Bonus if it tests the specific differing letters
                        tests_diff_letters = len(word_letters & diff_letters)
                        
                        score = -new_letter_bonus - tests_diff_letters
                        
                        if score < best_score:
                            best_score = score
                            best_distinguisher = word
            
            if best_distinguisher:
                print(f"Using distinguishing word: {best_distinguisher} (tests difference between {word1} and {word2})")
                return best_distinguisher
        
        # Fallback: just pick one of the answers
        print(f"No good distinguishing word found, guessing: {possible_words[0]}")
        return possible_words[0]
    
    # Rest of the original logic for larger sets...
    candidates = []
    letter_freq = get_letter_frequencies(possible_words)
    
    # IMPROVED evaluation set selection
    if words_remaining > ELIMINATION_THRESHOLD:
        # Force elimination mode - only consider non-answers
        evaluation_set = []
        for word in all_words[:800]:  # Check more elimination candidates
            if word not in possible_words:  # Must not be a possible answer
                # CRITICAL FIX: Skip words with excluded letters
                word_letters = set(word)
                if word_letters & excluded_letters:  # Contains excluded letters
                    continue  # Skip entirely
                
                # PRIORITIZE WORDS WITH UNEXPLORED LETTERS
                unexplored_letters = word_letters - known_letters - excluded_letters
                if len(unexplored_letters) >= 3:  # Must have at least 3 new letters
                    evaluation_set.append(word)
        
        # If not enough unexplored words, fall back to frequency-based
        if len(evaluation_set) < 50:
            for word in all_words[:800]:
                if word not in possible_words:
                    word_score = sum(letter_freq[char] for char in set(word))
                    if word_score > 0:
                        evaluation_set.append(word)
        
        evaluation_set = evaluation_set[:150]  # Top elimination candidates
        
    elif words_remaining > MEDIUM_SET_THRESHOLD:
        # Medium set: PRIORITIZE UNEXPLORED LETTERS
        elimination_words = []
        for word in all_words[:600]:
            if word not in possible_words:
                word_letters = set(word)
                unexplored_letters = word_letters - known_letters - excluded_letters
                if len(unexplored_letters) >= 2:  # At least 2 new letters
                    elimination_words.append((len(unexplored_letters), word))
        
        # Sort by number of unexplored letters (descending)
        elimination_words.sort(reverse=True)
        evaluation_set = [word for _, word in elimination_words[:100]]
        
    else:
        # Small set: use the specialized distinguishing function
        return find_best_distinguishing_word(possible_words, all_words, known_letters, excluded_letters)
    
    print(f"Evaluating {len(evaluation_set)} candidate words...")
    
    for i, word in enumerate(evaluation_set):
        max_remaining, avg_remaining, is_possible_answer, total_eliminated = evaluate_guess(word, possible_words, all_words)
        
        # ENHANCED scoring for unexplored letters
        word_letters = set(word)
        unexplored_letters = word_letters - known_letters - excluded_letters
        known_letters_in_word = len(word_letters & known_letters)
        
        # Base minimax score
        base_score = max_remaining
        tie_breaker = avg_remaining / 1000
        
        # Bonus for exploring new letters (MAJOR IMPROVEMENT)
        exploration_bonus = 0
        if not is_possible_answer and words_remaining > MEDIUM_SET_THRESHOLD:
            exploration_bonus = -len(unexplored_letters) * 0.5  # Strong bonus for new letters
            known_letter_penalty = known_letters_in_word * 0.3   # Penalty for reusing known letters
            exploration_bonus += known_letter_penalty
        
        # Answer vs elimination preference
        answer_bonus = 0
        if is_possible_answer:
            if words_remaining <= SMALL_SET_THRESHOLD or turn >= LATE_GAME_TURN:
                answer_bonus = -1.0  # Strong preference for answers in endgame
            else:
                answer_bonus = 2.0   # STRONG PENALTY for going for answers early
        else:
            if words_remaining > MEDIUM_SET_THRESHOLD:
                answer_bonus = -0.5  # Strong reward for elimination
        
        final_score = base_score + tie_breaker + answer_bonus + exploration_bonus
        
        candidates.append((final_score, word, max_remaining, avg_remaining, is_possible_answer, len(unexplored_letters), known_letters_in_word))
    
    # Sort by score (lower is better)
    candidates.sort()
    
    # Debug info for the top candidates
    print(f"\nTurn {turn}, {words_remaining} words remaining")
    print(f"Known letters: {sorted(known_letters) if known_letters else 'None'}")
    print(f"Excluded letters: {sorted(excluded_letters) if excluded_letters else 'None'}")
    print("Top candidates:")
    for i, (score, word, max_rem, avg_rem, is_ans, new_letters, known_count) in enumerate(candidates[:8]):
        ans_marker = " (ANSWER)" if is_ans else ""
        strategy = "ELIMINATE" if not is_ans else "ANSWER"
        print(f"  {word}: max={max_rem}, avg={avg_rem:.1f}, new={new_letters}, known={known_count}, score={score:.3f} [{strategy}]{ans_marker}")
    
    best_word = candidates[0][1]
    best_is_answer = candidates[0][4]
    strategy_chosen = "GOING FOR ANSWER" if best_is_answer else "ELIMINATING WORDS"
    
    print(f"\nCHOSEN: {best_word} - Strategy: {strategy_chosen}")
    
    return best_word

def parse_feedback_input(feedback_input: str) -> str:
    """
    Parse user feedback input into standard format.
    Accepts multiple formats:
    - G/Y/B: GYBBB
    - Colors: green/yellow/black or g/y/b
    - Numbers: 2 1 0 0 0 (2=green, 1=yellow, 0=black)
    - Emojis: 🟩🟨⬛⬛⬛
    """
    feedback_input = feedback_input.strip().upper()
    
    # Remove spaces and common separators
    feedback_input = feedback_input.replace(' ', '').replace(',', '').replace('-', '')
    
    # Handle different input formats
    if len(feedback_input) == 5:
        # Direct G/Y/B format
        if all(c in 'GYB' for c in feedback_input):
            return feedback_input
        
        # Handle color names
        color_map = {'G': 'G', 'Y': 'Y', 'B': 'B'}
        if all(c in color_map for c in feedback_input):
            return feedback_input
    
    # Handle number format (2=green, 1=yellow, 0=black)
    if all(c in '210' for c in feedback_input) and len(feedback_input) == 5:
        num_map = {'2': 'G', '1': 'Y', '0': 'B'}
        return ''.join(num_map[c] for c in feedback_input)
    
    # Handle emoji format
    emoji_map = {'🟩': 'G', '🟨': 'Y', '⬛': 'B', '⬜': 'B'}
    if any(emoji in feedback_input for emoji in emoji_map):
        result = ''
        for char in feedback_input:
            if char in emoji_map:
                result += emoji_map[char]
        if len(result) == 5:
            return result
    
    # Handle word format
    word_map = {'GREEN': 'G', 'YELLOW': 'Y', 'BLACK': 'B', 'GRAY': 'B', 'GREY': 'B'}
    for word, letter in word_map.items():
        feedback_input = feedback_input.replace(word, letter)
    
    if len(feedback_input) == 5 and all(c in 'GYB' for c in feedback_input):
        return feedback_input
    
    raise ValueError(f"Invalid feedback format: {feedback_input}")

def play_interactive_wordle():
    """
    Interactive Wordle helper - you play the game and input the feedback.
    """
    print("="*60)
    print("INTERACTIVE WORDLE HELPER")
    print("="*60)
    print("Instructions:")
    print("1. I'll suggest words for you to try")
    print("2. Enter the word in the actual Wordle game")
    print("3. Tell me the color feedback you got")
    print("4. I'll suggest the next word")
    print()
    print("Feedback formats you can use:")
    print("  G/Y/B: GYBBB (Green/Yellow/Black)")
    print("  Numbers: 21000 (2=Green, 1=Yellow, 0=Black)")
    print("  Emojis: 🟩🟨⬛⬛⬛")
    print("="*60)
    
    # Load word list
    try:
        words = load_words("T:/WordleCalculator/src/wordle.txt")
        print(f"Loaded {len(words)} words")
    except FileNotFoundError:
        print("Could not load word file. Using basic word list.")
        words = ["ADIEU", "AUDIO", "AROSE", "IRATE", "STARE", "SLATE", "COURT"]  # Basic fallback
    
    possible_words = words.copy()
    guesses = []
    
    # Track knowledge
    known_letters = set()
    known_positions = [''] * 5
    excluded_letters = set()
    wrong_positions = defaultdict(set)
    
    for turn in range(1, 7):
        print(f"\n{'='*40}")
        print(f"TURN {turn}")
        print(f"{'='*40}")
        print(f"Possible words remaining: {len(possible_words)}")
        
        if len(possible_words) <= 20:
            print(f"Remaining possibilities: {', '.join(possible_words[:20])}")
            if len(possible_words) > 20:
                print(f"... and {len(possible_words) - 20} more")
        
        # Get suggestion
        suggestion = choose_best_word(possible_words, words, turn, known_letters, excluded_letters)
        guesses.append(suggestion)
        
        print(f"\n🎯 SUGGESTED WORD: {suggestion}")
        print(f"   Enter '{suggestion}' in Wordle")
        
        # Get feedback from user
        while True:
            try:
                print(f"\nWhat feedback did you get for '{suggestion}'?")
                print("(Enter colors as: GYBBB, 21000, 🟩🟨⬛⬛⬛, or 'quit' to exit)")
                feedback_input = input("Feedback: ").strip()
                
                if feedback_input.lower() in ['quit', 'exit', 'q']:
                    print("Thanks for playing!")
                    return
                
                if feedback_input.lower() in ['won', 'win', 'solved', 'ggggg']:
                    feedback = "GGGGG"
                else:
                    feedback = parse_feedback_input(feedback_input)
                
                print(f"Interpreted as: {feedback}")
                break
                
            except ValueError as e:
                print(f"Error: {e}")
                print("Please try again with a valid format.")
        
        # Check if won
        if feedback == "GGGGG":
            print(f"\n🎉 CONGRATULATIONS! Solved in {turn} tries!")
            print(f"Guesses: {' -> '.join(guesses)}")
            return
        
        # Update knowledge
        for i, (letter, fb) in enumerate(zip(suggestion, feedback)):
            if fb == 'G':  # Green - correct position
                known_positions[i] = letter
                known_letters.add(letter)
            elif fb == 'Y':  # Yellow - wrong position
                known_letters.add(letter)
                wrong_positions[letter].add(i)
            else:  # Black - not in word (unless it's a duplicate)
                if letter not in known_letters:
                    excluded_letters.add(letter)
        
        # Filter possible words
        possible_words = filter_words(possible_words, suggestion, feedback)
        
        print(f"\nUpdated knowledge:")
        print(f"  Known letters: {sorted(known_letters) if known_letters else 'None'}")
        print(f"  Excluded letters: {sorted(excluded_letters) if excluded_letters else 'None'}")
        
        # Show pattern
        pattern = ""
        for i, letter in enumerate(known_positions):
            if letter:
                pattern += letter
            else:
                pattern += "_"
        print(f"  Pattern: {pattern}")
        
        if len(possible_words) == 0:
            print("\n❌ No valid words remaining! There might be an error in the feedback.")
            print("The target word might not be in my dictionary.")
            return
    
    print(f"\n😞 Didn't solve it in 6 tries!")
    print(f"Final guesses: {' -> '.join(guesses)}")
    if len(possible_words) <= 10:
        print(f"Remaining possibilities were: {', '.join(possible_words)}")

if __name__ == "__main__":
    print("WORDLE SOLVER")
    print("Choose mode:")
    print("1. Interactive helper (play real Wordle)")
    print("2. Auto-solve specific word")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        play_interactive_wordle()
    else:
        # Original auto-solve mode
        try:
            words = load_words("T:/WordleCalculator/src/wordle.txt")
            print(f"Loaded {len(words)} words")
            
            target = input("Enter target word to solve: ").strip().upper()
            
            if target not in words:
                print(f"Warning: '{target}' not in word list. Using it anyway...")
            
            # Auto-solve mode (original functionality)
            def solve_wordle_auto(target_word: str, word_list: List[str]) -> Tuple[List[str], int]:
                possible_words = word_list.copy()
                guesses = []
                known_letters = set()
                excluded_letters = set()
                
                print(f"Solving for: {target_word}")
                print(f"Starting with {len(possible_words)} possible words")
                
                for turn in range(1, 7):
                    guess = choose_best_word(possible_words, word_list, turn, known_letters, excluded_letters)
                    guesses.append(guess)
                    
                    feedback = get_feedback(guess, target_word)
                    print(f"\nGuess {turn}: {guess}")
                    print(f"Feedback: {feedback}")
                    
                    # Update knowledge
                    for i, (letter, fb) in enumerate(zip(guess, feedback)):
                        if fb == 'G':
                            known_letters.add(letter)
                        elif fb == 'Y':
                            known_letters.add(letter)
                        else:
                            if letter not in known_letters:
                                excluded_letters.add(letter)
                    
                    if feedback == "GGGGG":
                        print(f"Solved in {turn} tries!")
                        return guesses, turn
                    
                    possible_words = filter_words(possible_words, guess, feedback)
                    print(f"Remaining possibilities: {len(possible_words)}")
                    
                    if len(possible_words) <= 10:
                        print(f"Remaining words: {possible_words}")
                
                print("Failed to solve in 6 tries!")
                return guesses, 7
            
            solve_wordle_auto(target, words)
            
        except FileNotFoundError:
            print("Please make sure 'wordle.txt' exists in the src directory")