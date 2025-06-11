import os

def convert_word_list():
    filename = 'T:\\WordleCalculator\\src\\wordleUC.txt'
    
    # Check if file exists and get info
    if os.path.exists(filename):
        file_size = os.path.getsize(filename)
        print(f"File exists, size: {file_size} bytes")
    else:
        print(f"File does not exist: {filename}")
        return
    
    # Read the file with different encodings if needed
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"Raw content length: {len(content)}")
        print(f"Content preview (first 200 chars): '{content[:200]}'")
        
        # Strip and split
        content = content.strip()
        words = content.split()
        
        print(f"Found {len(words)} words after splitting")
        if len(words) > 0:
            print(f"First word: '{words[0]}'")
            print(f"Last word: '{words[-1]}'")
        
        # Write each word on a new line
        with open('T:\\WordleCalculator\\src\\wordle_words.txt', 'w') as f:
            for word in words:
                if word.strip():  # Only write non-empty words
                    f.write(word.strip() + '\n')
        
        print(f"Converted {len(words)} words to wordle_words.txt")
        
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    convert_word_list()