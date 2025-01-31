def normalizeString(s: str):
    """
    Normalize a string by:
    - Converting to lowercase
    - Removing non-alphanumeric characters
    - Stripping white spaces
    """
    s = s.lower()
    s = ''.join(e for e in s if e.isalnum())
    return s

def jaroSimilarity(s1: str, s2: str):
    """
    Calculate the Jaro similarity between two strings.
    """
    if not s1 or not s2:
        return 0.0
    
    s1 = normalizeString(s1)
    s2 = normalizeString(s2)

    # Proximity threshold for characters to be considered matching
    match_distance = (max(len(s1), len(s2)) // 2) - 1
    
    # Lists to keep track of matched characters
    s1_matches = [False] * len(s1)
    s2_matches = [False] * len(s2)
    
    # Count matching characters
    matches = 0
    for i, char in enumerate(s1):
        start = max(0, i - match_distance)
        end = min(len(s2), i + match_distance + 1)
        for j in range(start, end):
            if s2_matches[j]: continue
            if char != s2[j]: continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break
    
    if matches == 0: return 0.0
    
    # Count transpositions (half the number of unmatched characters among the matching ones)
    transpositions = 0
    k = 0
    for i, char in enumerate(s1):
        if not s1_matches[i]: continue
        while not s2_matches[k]:
            k += 1
        if char != s2[k]:
            transpositions += 1
        k += 1
    
    jaro = ((matches / len(s1)) + (matches / len(s2)) + ((matches - transpositions // 2) / matches)) / 3.0
    return jaro

def doFuzzyMatch(s1: str, s2: str, p=0.1):
    """
    Calculate the Jaro-Winkler similarity between two strings.
    """
    jaro_sim = jaroSimilarity(s1, s2)
    prefix_len = 0
    for c1, c2 in zip(s1, s2):
        if c1 == c2:
            prefix_len += 1
        else:
            break
    prefix_len = min(prefix_len, 4)  # Common prefix length should not exceed 4
    return jaro_sim + (prefix_len * p * (1 - jaro_sim))

def findBestMatch(s: str, candidates: list, p=0.1):
    """
    Find the string in the list of candidates that has the highest Jaro-Winkler similarity to the input string.
    """
    best_match = None
    highest_similarity = 0.0
    
    for candidate in candidates:
        similarity = doFuzzyMatch(s, candidate, p)
        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match = candidate
    
    return best_match